"""Tests for ChangeTracker."""

import pytest
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.models import Change, ChangeType
from cinchdb.config import Config


class TestChangeTracker:
    """Test change tracking functionality."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        
        # Initialize project
        config = Config(project_dir)
        config.init_project()
        
        yield project_dir
        shutil.rmtree(temp)
    
    @pytest.fixture
    def change_tracker(self, temp_project):
        """Create a ChangeTracker instance."""
        return ChangeTracker(temp_project, "main", "main")
    
    def test_get_changes_empty(self, change_tracker):
        """Test getting changes from empty branch."""
        changes = change_tracker.get_changes()
        assert changes == []
    
    def test_add_change(self, change_tracker):
        """Test adding a change."""
        # Create a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            details={
                "columns": [
                    {"name": "id", "type": "TEXT"},
                    {"name": "name", "type": "TEXT"},
                    {"name": "email", "type": "TEXT"}
                ]
            },
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, email TEXT)"
        )
        
        # Add it
        added_change = change_tracker.add_change(change)
        
        # Should have ID and timestamp
        assert added_change.id is not None
        assert added_change.created_at is not None
        
        # Should be in the list
        changes = change_tracker.get_changes()
        assert len(changes) == 1
        assert changes[0].entity_name == "users"
    
    def test_add_multiple_changes(self, change_tracker):
        """Test adding multiple changes."""
        # Add table
        table_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)"
        )
        change_tracker.add_change(table_change)
        
        # Add column
        column_change = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name="email",
            branch="main",
            details={"table": "users", "column_type": "TEXT"},
            sql="ALTER TABLE users ADD COLUMN email TEXT"
        )
        change_tracker.add_change(column_change)
        
        # Should have both
        changes = change_tracker.get_changes()
        assert len(changes) == 2
        assert changes[0].type == ChangeType.CREATE_TABLE
        assert changes[1].type == ChangeType.ADD_COLUMN
    
    def test_get_unapplied_changes(self, change_tracker):
        """Test getting only unapplied changes."""
        # Add some changes
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
            applied=True
        )
        change_tracker.add_change(change1)
        
        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="posts",
            branch="main",
            sql="CREATE TABLE posts (id TEXT PRIMARY KEY)",
            applied=False
        )
        change_tracker.add_change(change2)
        
        # Get unapplied
        unapplied = change_tracker.get_unapplied_changes()
        assert len(unapplied) == 1
        assert unapplied[0].entity_name == "posts"
    
    def test_mark_change_applied(self, change_tracker):
        """Test marking a change as applied."""
        # Add a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)"
        )
        added = change_tracker.add_change(change)
        
        # Should be unapplied
        assert not added.applied
        
        # Mark as applied
        change_tracker.mark_change_applied(added.id)
        
        # Should now be applied
        changes = change_tracker.get_changes()
        assert changes[0].applied
        
        # Should not be in unapplied list
        unapplied = change_tracker.get_unapplied_changes()
        assert len(unapplied) == 0
    
    def test_get_changes_since(self, change_tracker):
        """Test getting changes since a specific change."""
        # Add multiple changes
        changes = []
        for i in range(5):
            change = Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name=f"table{i}",
                branch="main",
                sql=f"CREATE TABLE table{i} (id TEXT PRIMARY KEY)"
            )
            added = change_tracker.add_change(change)
            changes.append(added)
        
        # Get changes since the 3rd one
        since_changes = change_tracker.get_changes_since(changes[2].id)
        
        # Should have changes 3 and 4 (after change 2)
        assert len(since_changes) == 2
        assert since_changes[0].entity_name == "table3"
        assert since_changes[1].entity_name == "table4"
    
    def test_clear_changes(self, change_tracker):
        """Test clearing all changes."""
        # Add some changes
        for i in range(3):
            change = Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name=f"table{i}",
                branch="main",
                sql=f"CREATE TABLE table{i} (id TEXT PRIMARY KEY)"
            )
            change_tracker.add_change(change)
        
        # Should have changes
        assert len(change_tracker.get_changes()) == 3
        
        # Clear them
        change_tracker.clear_changes()
        
        # Should be empty
        assert len(change_tracker.get_changes()) == 0
    
    def test_has_change_id(self, change_tracker):
        """Test checking if a change ID exists."""
        # Add a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)"
        )
        added = change_tracker.add_change(change)
        
        # Should exist
        assert change_tracker.has_change_id(added.id)
        
        # Non-existent should not
        assert not change_tracker.has_change_id("non-existent-id")
    
    def test_persistence(self, change_tracker, temp_project):
        """Test that changes persist to disk."""
        # Add a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)"
        )
        change_tracker.add_change(change)
        
        # Create new tracker instance
        new_tracker = ChangeTracker(temp_project, "main", "main")
        
        # Should still have the change
        changes = new_tracker.get_changes()
        assert len(changes) == 1
        assert changes[0].entity_name == "users"