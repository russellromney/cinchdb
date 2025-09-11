"""Test database name validation."""

import tempfile
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database
from cinchdb.utils.name_validator import InvalidNameError


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