"""Test path traversal security protections."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.utils.name_validator import validate_name, InvalidNameError
from cinchdb.managers.base import ConnectionContext
from cinchdb.core.path_utils import get_tenant_db_path, ensure_tenant_db_path
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.initializer import init_project


class TestPathTraversalSecurity:
    """Test that path traversal attacks are prevented."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        init_project(project_dir)
        yield project_dir
        shutil.rmtree(temp)
    
    def test_validate_name_blocks_path_traversal(self):
        """Test that validate_name blocks path traversal attempts."""
        # Test various path traversal attempts
        dangerous_names = [
            "../evil",
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "tenant/../../../etc",
            "tenant/../../",
            "~/.ssh/id_rsa",
            "/etc/passwd",
            "\\windows\\system32",
            "tenant\x00.db",  # Null byte injection
            "tenant\r\n.db",  # CRLF injection
            "tenant\t.db",    # Tab character
        ]
        
        for name in dangerous_names:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name, "tenant")
            assert "Security violation" in str(exc_info.value) or "Invalid" in str(exc_info.value)
    
    def test_validate_name_blocks_periods(self):
        """Test that periods are no longer allowed in names."""
        invalid_names = [
            "tenant.db",
            "tenant.test",
            "tenant..name",
            "tenant.",
            ".tenant",
        ]
        
        for name in invalid_names:
            with pytest.raises(InvalidNameError):
                validate_name(name, "tenant")
    
    def test_path_utils_validates_names(self, temp_project):
        """Test that path utilities validate names."""
        # Test get_tenant_db_path validates all parameters
        with pytest.raises(InvalidNameError):
            get_tenant_db_path(temp_project, "../evil", "main", "tenant")
        
        with pytest.raises(InvalidNameError):
            get_tenant_db_path(temp_project, "main", "../evil", "tenant")
        
        with pytest.raises(InvalidNameError):
            get_tenant_db_path(temp_project, "main", "main", "../evil")
        
        # Test ensure_tenant_db_path also validates
        with pytest.raises(InvalidNameError):
            ensure_tenant_db_path(temp_project, "main", "main", "../../etc/passwd")
    
    def test_tenant_manager_validates_names(self, temp_project):
        """Test that TenantManager validates names."""
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        
        # Test create_tenant validates
        with pytest.raises(InvalidNameError):
            tenant_mgr.create_tenant("../evil")
        
        with pytest.raises(InvalidNameError):
            tenant_mgr.create_tenant("tenant/../../../etc")
        
        # Test delete_tenant validates
        with pytest.raises(InvalidNameError):
            tenant_mgr.delete_tenant("../evil")
        
        # Test rename_tenant validates both names
        tenant_mgr.create_tenant("valid-tenant")
        
        with pytest.raises(InvalidNameError):
            tenant_mgr.rename_tenant("valid-tenant", "../evil")
        
        with pytest.raises(InvalidNameError):
            tenant_mgr.rename_tenant("../evil", "new-name")
        
        # Test get_tenant_connection validates
        with pytest.raises(InvalidNameError):
            tenant_mgr.get_tenant_connection("../evil")
        
        # Test materialize_tenant validates
        with pytest.raises(InvalidNameError):
            tenant_mgr.materialize_tenant("../evil")
    
    def test_valid_names_still_work(self, temp_project):
        """Test that valid names still work."""
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        
        valid_names = [
            "tenant1",
            "customer-a",
            "user_123",
            "test-tenant-with-long-name",
            "a",  # Single character
            "123",  # Numbers only
        ]
        
        for name in valid_names:
            # Should not raise any exceptions
            validate_name(name, "tenant")
            tenant_mgr.create_tenant(name, lazy=True)
    
    def test_reserved_names_blocked(self):
        """Test that Windows reserved names are blocked."""
        reserved = ["con", "prn", "aux", "nul", "com1", "lpt1"]
        
        for name in reserved:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name, "tenant")
            assert "reserved name" in str(exc_info.value)
    
    def test_control_characters_blocked(self):
        """Test that control characters are blocked."""
        control_chars = [
            "tenant\x00",  # Null byte
            "tenant\x01",  # SOH
            "tenant\x1f",  # Unit separator
            "tenant\r",    # Carriage return
            "tenant\n",    # Line feed
        ]
        
        for name in control_chars:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name, "tenant")
            assert "control characters" in str(exc_info.value)