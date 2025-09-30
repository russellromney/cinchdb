"""Test database name validation."""

import tempfile
import shutil
import time
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database
from cinchdb.managers.base import ConnectionContext
from cinchdb.utils.name_validator import InvalidNameError, validate_name
from cinchdb.managers.table import TableManager
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.models.table import Column


def test_database_name_validation():
    """Test that database names are validated at creation time."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Valid database names should work
        init_database(project_dir, "valid-database", lazy=True)
        init_database(project_dir, "db123", lazy=True)
        init_database(project_dir, "test-db-456", lazy=True)
        init_database(project_dir, "db_with_underscore", lazy=True)
        
        # Invalid database names should fail
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "Invalid Database", lazy=True)
        assert "lowercase" in str(exc.value).lower()
        
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "UPPERCASE", lazy=True)
        assert "lowercase" in str(exc.value).lower()
        
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "-starts-with-dash", lazy=True)
        assert "start and end with" in str(exc.value).lower()
        
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "ends-with-dash-", lazy=True)
        assert "start and end with" in str(exc.value).lower()
        
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "special!char", lazy=True)
        assert "lowercase" in str(exc.value).lower() or "alphanumeric" in str(exc.value).lower()
        
        # Periods no longer allowed for security
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "my.database", lazy=True)
        assert "security violation" in str(exc.value).lower() or "invalid" in str(exc.value).lower()
        
        # Reserved names should fail
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "con", lazy=True)
        assert "reserved" in str(exc.value).lower()
        
        with pytest.raises(InvalidNameError) as exc:
            init_database(project_dir, "nul", lazy=True)
        assert "reserved" in str(exc.value).lower()


def test_initial_database_name_validation():
    """Test that initial database name is validated when creating project."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Invalid initial database name should fail
        with pytest.raises(InvalidNameError) as exc:
            init_project(project_dir, database_name="Invalid Name")
        assert "lowercase" in str(exc.value).lower()
        
        # Valid initial database name should work
        init_project(project_dir, database_name="valid-name")
        
        # Check project was created
        assert (project_dir / ".cinchdb").exists()


class TestComprehensiveValidation:
    """Test comprehensive name validation for all entity types."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir)
        init_project(project_root, database_name="testdb")
        yield project_root
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_database_name_edge_cases(self, temp_project):
        """Test database name validation edge cases."""
        # Valid edge cases
        valid_names = [
            "a",  # Single character
            "db",  # Two characters
            "my-database",  # With hyphen
            "my_database",  # With underscore
            "db123",  # With numbers
            "test-db-456",  # Mixed
            "x" * 63,  # Maximum length (63 chars)
        ]
        
        for name in valid_names:
            init_database(temp_project, name, lazy=True)
        
        # Invalid edge cases
        invalid_cases = [
            ("", "empty"),
            ("x" * 64, "too long"),
            ("My-Database", "uppercase"),
            ("my database", "space"),
            ("my.database", "period"),
            ("../etc/passwd", "path traversal"),
            ("con", "reserved Windows"),
            ("prn", "reserved Windows"),
            ("aux", "reserved Windows"),
            ("nul", "reserved Windows"),
            ("com1", "reserved Windows"),
            ("lpt1", "reserved Windows"),
            ("-database", "starts with hyphen"),
            ("database-", "ends with hyphen"),
            ("_database", "starts with underscore"),
            ("database_", "ends with underscore"),
            ("data@base", "special char @"),
            ("data#base", "special char #"),
            ("data$base", "special char $"),
            ("data%base", "special char %"),
            ("data&base", "special char &"),
            ("data*base", "special char *"),
            ("data(base", "special char ("),
            ("data)base", "special char )"),
            ("data[base", "special char ["),
            ("data]base", "special char ]"),
            ("data{base", "special char {"),
            ("data}base", "special char }"),
            ("data|base", "special char |"),
            ("data\\base", "special char \\"),
            ("data/base", "special char /"),
            ("data:base", "special char :"),
            ("data;base", "special char ;"),
            ("data'base", "special char '"),
            ('data"base', 'special char "'),
            ("data<base", "special char <"),
            ("data>base", "special char >"),
            ("data?base", "special char ?"),
            ("data`base", "special char `"),
            ("data~base", "special char ~"),
            ("data!base", "special char !"),
            ("data=base", "special char ="),
            ("data+base", "special char +"),
            ("🔥database", "emoji"),
            ("データベース", "Japanese"),
            ("база_данных", "Cyrillic"),
            ("قاعدة_البيانات", "Arabic"),
            ("\x00database", "null byte"),
            ("data\nbase", "newline"),
            ("data\tbase", "tab"),
            ("data\rbase", "carriage return"),
        ]
        
        for name, reason in invalid_cases:
            try:
                with pytest.raises(InvalidNameError) as exc:
                    init_database(temp_project, name, lazy=True)
                # Error message should be informative
                assert len(str(exc.value)) > 0, f"No error message for {reason}"
            except:
                print(f"Failed to reject invalid name: '{name}' (reason: {reason})")
                raise

    def test_table_name_validation(self, temp_project):
        """Test table name validation edge cases."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))

        # Valid table names (no hyphens allowed)
        valid_names = [
            "users",
            "user_profiles",
            "t",  # Single char
            "t123",
            "table_123_test",
            "x" * 50,  # Long name test
        ]
        
        for name in valid_names:
            table_mgr.create_table(name, [Column(name="test_col", type="INTEGER")])
        
        # Invalid table names
        invalid_names = [
            "",  # Empty
            "x" * 64,  # Too long
            "Table",  # Uppercase
            "my table",  # Space
            "user-profiles",  # Hyphen (not allowed in tables)
            "__cdc_table",  # System prefix
            "sqlite_master",  # SQLite reserved
            "sqlite_sequence",  # SQLite reserved
            "-table",  # Starts with hyphen
            "_table",  # Starts with underscore
            "table-",  # Ends with hyphen
            "table_",  # Ends with underscore
            "table.name",  # Period
            "../table",  # Path traversal
            "table@name",  # Special char
            "table#name",  # Special char
            "🔥table",  # Emoji
            "テーブル",  # Japanese
            "123table",  # Starts with number (tables must start with letter)
        ]
        
        for name in invalid_names:
            with pytest.raises((InvalidNameError, ValueError)):
                table_mgr.create_table(name, [Column(name="test_col", type="INTEGER")])

    def test_column_name_validation(self, temp_project):
        """Test column name validation edge cases."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))

        # Valid column names (no hyphens, no 'id' as it's protected)
        valid_columns = [
            "user_id",
            "c",  # Single char
            "col123",
            "column_123_test",
            "x" * 50,  # Long name test
        ]
        
        for i, col_name in enumerate(valid_columns):
            # Use a short table name to avoid length issues
            table_mgr.create_table(
                f"t{i}",
                [Column(name=col_name, type="INTEGER")]
            )
        
        # Invalid column names
        invalid_columns = [
            "",  # Empty
            "x" * 64,  # Too long
            "Column",  # Uppercase
            "my column",  # Space
            "user-id",  # Hyphen (not allowed in columns)
            "-column",  # Starts with hyphen
            "_column",  # Starts with underscore
            "column-",  # Ends with hyphen
            "column_",  # Ends with underscore
            "column.name",  # Period
            "column@name",  # Special char
            "🔥column",  # Emoji
            "123column",  # Starts with number (columns must start with letter)
            "id",  # Protected column name
        ]
        
        for col_name in invalid_columns:
            with pytest.raises((InvalidNameError, ValueError)):
                table_mgr.create_table(
                    "test_table",
                    [Column(name=col_name, type="INTEGER")]
                )

    def test_branch_name_validation(self, temp_project):
        """Test branch name validation edge cases."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))
        
        # Valid branch names
        valid_names = [
            "feature",
            "feature-123",
            "feature_123",
            "b",  # Single char
            "branch123",
            "x" * 50,  # Long name test
        ]
        
        for name in valid_names:
            branch_mgr.create_branch("main", name)
        
        # Invalid branch names
        invalid_names = [
            "",  # Empty
            "x" * 64,  # Too long
            "Feature",  # Uppercase
            "my branch",  # Space
            "-branch",  # Starts with hyphen
            "_branch",  # Starts with underscore
            "branch-",  # Ends with hyphen
            "branch_",  # Ends with underscore
            "branch.name",  # Period
            "../branch",  # Path traversal
            "branch@name",  # Special char
            "🔥branch",  # Emoji
        ]
        
        for name in invalid_names:
            with pytest.raises((InvalidNameError, ValueError)):
                branch_mgr.create_branch("main", name)

    def test_tenant_name_validation(self, temp_project):
        """Test tenant name validation edge cases."""
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))

        # Valid tenant names
        valid_names = [
            "tenant",
            "tenant-123",
            "tenant_123",
            "t",  # Single char
            "tenant123",
            "x" * 50,  # Long name test
        ]
        
        for name in valid_names:
            tenant_mgr.create_tenant(name, lazy=True)
        
        # Invalid tenant names
        invalid_names = [
            "",  # Empty
            "x" * 64,  # Too long
            "Tenant",  # Uppercase
            "my tenant",  # Space
            "-tenant",  # Starts with hyphen
            "_tenant",  # Starts with underscore
            "tenant-",  # Ends with hyphen
            "tenant_",  # Ends with underscore
            "tenant.name",  # Period
            "../tenant",  # Path traversal
            "tenant@name",  # Special char
            "🔥tenant",  # Emoji
            "__empty__",  # Reserved name
        ]
        
        for name in invalid_names:
            with pytest.raises((InvalidNameError, ValueError)):
                tenant_mgr.create_tenant(name, lazy=True)

    def test_path_traversal_attempts(self, temp_project):
        """Test path traversal attack prevention."""
        path_traversal_attempts = [
            "../etc/passwd",
            "../../etc/shadow",
            "../../../root/.ssh/id_rsa",
            "..\\windows\\system32",
            "./../database",
            "database/../../../etc",
            "database/../../",
            "%2e%2e%2f",  # URL encoded ../
            "..%2F",  # Mixed encoding
            "database\x00../etc",  # Null byte injection
        ]
        
        for attempt in path_traversal_attempts:
            # Database names
            with pytest.raises(InvalidNameError):
                init_database(temp_project, attempt, lazy=True)

            # Table names
            table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))
            with pytest.raises((InvalidNameError, ValueError)):
                table_mgr.create_table(attempt, [Column(name="test_col", type="INTEGER")])

            # Branch names
            branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))
            with pytest.raises((InvalidNameError, ValueError)):
                branch_mgr.create_branch("main", attempt)

            # Tenant names
            tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))
            with pytest.raises((InvalidNameError, ValueError)):
                tenant_mgr.create_tenant(attempt, lazy=True)

    def test_unicode_names(self, temp_project):
        """Test Unicode character handling in names."""
        unicode_names = [
            "こんにちは",  # Japanese
            "你好",  # Chinese
            "مرحبا",  # Arabic
            "שלום",  # Hebrew
            "Здравствуйте",  # Russian
            "🔥💯🎉",  # Emojis
            "café",  # Latin with diacritics
            "naïve",  # More diacritics
            "Ω",  # Greek
            "™",  # Symbols
            "♠♣♥♦",  # Card suits
            "①②③",  # Circled numbers
        ]
        
        for name in unicode_names:
            # All should be rejected (not lowercase alphanumeric)
            with pytest.raises(InvalidNameError):
                validate_name(name, "test")

    def test_maximum_length_boundaries(self):
        """Test exact boundary conditions for name lengths."""
        # Test at boundaries: 0, 1, 62, 63, 64 characters
        test_cases = [
            (0, False),  # Empty - invalid
            (1, True),   # Single char - valid
            (62, True),  # Just under max - valid
            (63, True),  # Exactly max - valid
            (64, False), # Just over max - invalid
            (65, False), # Well over max - invalid
            (100, False), # Way over max - invalid
        ]
        
        for length, should_be_valid in test_cases:
            name = "a" * length if length > 0 else ""
            
            if should_be_valid:
                validate_name(name, "test")  # Should not raise
            else:
                with pytest.raises(InvalidNameError):
                    validate_name(name, "test")

    def test_windows_reserved_names(self):
        """Test Windows reserved names are rejected."""
        # https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
        reserved_names = [
            "con", "prn", "aux", "nul",
            "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
            "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
        ]
        
        for name in reserved_names:
            with pytest.raises(InvalidNameError) as exc:
                validate_name(name, "test")
            assert "reserved" in str(exc.value).lower()
            
            # Test that adding suffix makes it valid (no longer exactly reserved)
            # This should NOT raise since "con-db" is not the same as "con"
            validate_name(f"{name}-db", "test")

    def test_performance_with_many_validations(self):
        """Test validation performance with many names."""
        import time
        
        # Generate 10,000 names to validate
        names = [f"database_{i:05d}" for i in range(10000)]
        
        start = time.time()
        for name in names:
            validate_name(name, "test")
        elapsed = time.time() - start
        
        # Should validate 10,000 names in under 1 second
        assert elapsed < 1.0, f"Validation too slow: {elapsed:.2f}s for 10,000 names"