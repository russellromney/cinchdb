"""Tests for CinchDB data models."""

import pytest
from datetime import datetime
from cinchdb.models import (
    Project, Database, Branch, Tenant, 
    Table, Column, Change, ChangeType
)


class TestModels:
    """Test data models."""
    
    def test_project_creation(self):
        """Test creating a project."""
        project = Project(
            name="test_project",
            path="/tmp/test"
        )
        
        assert project.name == "test_project"
        assert str(project.path) == "/tmp/test"
        assert project.active_database == "main"
        assert project.databases == []
    
    def test_database_creation(self):
        """Test creating a database."""
        db = Database(name="test_db")
        
        assert db.name == "test_db"
        assert db.branches == ["main"]
        assert db.active_branch == "main"
    
    def test_branch_creation(self):
        """Test creating a branch."""
        branch = Branch(
            name="feature",
            database="test_db",
            parent_branch="main"
        )
        
        assert branch.name == "feature"
        assert branch.database == "test_db"
        assert branch.parent_branch == "main"
        assert branch.tenants == ["main"]
        assert not branch.is_main
    
    def test_tenant_creation(self):
        """Test creating a tenant."""
        tenant = Tenant(
            name="customer1",
            branch="main",
            database="test_db"
        )
        
        assert tenant.name == "customer1"
        assert tenant.branch == "main"
        assert tenant.database == "test_db"
        assert not tenant.is_main
    
    def test_table_creation_with_defaults(self):
        """Test creating a table with default columns."""
        table = Table(name="users")
        
        assert table.name == "users"
        assert len(table.columns) == 3  # id, created_at, updated_at
        
        # Check default columns
        col_names = [col.name for col in table.columns]
        assert "id" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        
        # Check id column properties
        id_col = next(col for col in table.columns if col.name == "id")
        assert id_col.type == "TEXT"
        assert id_col.primary_key
        assert not id_col.nullable
    
    def test_table_creation_with_custom_columns(self):
        """Test creating a table with custom columns."""
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="age", type="INTEGER"),
            Column(name="email", type="TEXT", unique=True)
        ]
        
        table = Table(name="users", columns=columns)
        
        # Should have custom columns plus defaults
        assert len(table.columns) == 6  # 3 custom + 3 defaults
        assert table.columns[0].name == "id"  # id is always first
        assert table.columns[1].name == "name"
        assert table.columns[2].name == "age"
        assert table.columns[3].name == "email"
    
    def test_change_creation(self):
        """Test creating a change record."""
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            details={"columns": ["name", "email"]},
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, email TEXT)"
        )
        
        assert change.type == ChangeType.CREATE_TABLE
        assert change.entity_type == "table"
        assert change.entity_name == "users"
        assert change.branch == "feature"
        assert not change.applied
        assert "columns" in change.details
        # Change model should have table fields since it's stored in DB
        assert change.id is not None
        assert isinstance(change.created_at, datetime)
    
    def test_database_can_delete(self):
        """Test database deletion rules."""
        main_db = Database(name="main")
        other_db = Database(name="test")
        
        assert not main_db.can_delete()
        assert other_db.can_delete()
    
    def test_branch_can_delete(self):
        """Test branch deletion rules."""
        main_branch = Branch(name="main", database="test", is_main=True)
        feature_branch = Branch(name="feature", database="test")
        
        assert not main_branch.can_delete()
        assert feature_branch.can_delete()
    
    def test_tenant_can_delete(self):
        """Test tenant deletion rules."""
        main_tenant = Tenant(name="main", branch="main", database="test", is_main=True)
        other_tenant = Tenant(name="customer1", branch="main", database="test")
        
        assert not main_tenant.can_delete()
        assert other_tenant.can_delete()