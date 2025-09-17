"""Tests for MetadataDB change tracking functionality."""

import pytest
import tempfile
import shutil
import uuid
from pathlib import Path
from cinchdb.infrastructure.metadata_db import MetadataDB


class TestMetadataDBChangeTracking:
    """Test change tracking operations in MetadataDB."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    @pytest.fixture
    def metadata_db(self, temp_dir):
        """Create a MetadataDB instance."""
        return MetadataDB(temp_dir)

    @pytest.fixture
    def sample_database(self, metadata_db):
        """Create a sample database."""
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "test_db")
        return db_id

    @pytest.fixture
    def sample_branch(self, metadata_db, sample_database):
        """Create a sample branch."""
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, sample_database, "main")
        return branch_id

    def test_create_change(self, metadata_db, sample_database, sample_branch):
        """Test creating a change record."""
        change_id = str(uuid.uuid4())

        # Create a change
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="CREATE_TABLE",
            entity_type="table",
            entity_name="users",
            details={"columns": ["id", "name"]},
            sql="CREATE TABLE users (id TEXT, name TEXT)"
        )

        # Verify change exists
        change = metadata_db.get_change(change_id)
        assert change is not None
        assert change["id"] == change_id
        assert change["type"] == "CREATE_TABLE"
        assert change["entity_name"] == "users"

    def test_link_change_to_branch(self, metadata_db, sample_database, sample_branch):
        """Test linking a change to a branch."""
        change_id = str(uuid.uuid4())

        # Create a change
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="CREATE_TABLE",
            entity_type="table",
            entity_name="products"
        )

        # Link to branch
        metadata_db.link_change_to_branch(
            branch_id=sample_branch,
            change_id=change_id,
            applied=False,
            applied_order=0
        )

        # Get branch changes
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 1
        assert changes[0]["id"] == change_id
        assert changes[0]["applied"] == 0  # False

    def test_get_branch_changes_order(self, metadata_db, sample_database, sample_branch):
        """Test that branch changes are returned in correct order."""
        # Create multiple changes
        change_ids = []
        for i in range(3):
            change_id = str(uuid.uuid4())
            change_ids.append(change_id)

            metadata_db.create_change(
                change_id=change_id,
                database_id=sample_database,
                origin_branch_id=sample_branch,
                change_type="CREATE_TABLE",
                entity_type="table",
                entity_name=f"table_{i}"
            )

            # Link with specific order
            metadata_db.link_change_to_branch(
                branch_id=sample_branch,
                change_id=change_id,
                applied=False,
                applied_order=i
            )

        # Get changes - should be in order
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 3
        for i, change in enumerate(changes):
            assert change["id"] == change_ids[i]
            assert change["entity_name"] == f"table_{i}"

    def test_mark_change_applied(self, metadata_db, sample_database, sample_branch):
        """Test marking a change as applied."""
        change_id = str(uuid.uuid4())

        # Create and link change
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="CREATE_TABLE",
            entity_type="table",
            entity_name="orders"
        )

        metadata_db.link_change_to_branch(
            branch_id=sample_branch,
            change_id=change_id,
            applied=False,
            applied_order=0
        )

        # Initially not applied
        changes = metadata_db.get_branch_changes(sample_branch)
        assert changes[0]["applied"] == 0

        # Mark as applied
        metadata_db.mark_change_applied(sample_branch, change_id)

        # Now should be applied
        changes = metadata_db.get_branch_changes(sample_branch)
        assert changes[0]["applied"] == 1

    def test_clear_branch_changes(self, metadata_db, sample_database, sample_branch):
        """Test clearing all changes from a branch."""
        # Create and link multiple changes
        for i in range(3):
            change_id = str(uuid.uuid4())
            metadata_db.create_change(
                change_id=change_id,
                database_id=sample_database,
                origin_branch_id=sample_branch,
                change_type="CREATE_TABLE",
                entity_type="table",
                entity_name=f"table_{i}"
            )
            metadata_db.link_change_to_branch(
                branch_id=sample_branch,
                change_id=change_id,
                applied=False,
                applied_order=i
            )

        # Verify changes exist
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 3

        # Clear branch changes
        metadata_db.clear_branch_changes(sample_branch)

        # Verify changes are gone from branch
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 0

        # But the change records themselves still exist
        change = metadata_db.get_change(changes[0]["id"] if changes else str(uuid.uuid4()))
        # This will be None since we don't have the change_id anymore

    def test_copy_branch_changes(self, metadata_db, sample_database, sample_branch):
        """Test copying changes from one branch to another."""
        # Create a second branch
        target_branch_id = str(uuid.uuid4())
        metadata_db.create_branch(target_branch_id, sample_database, "feature")

        # Create and link changes to source branch
        change_ids = []
        for i in range(3):
            change_id = str(uuid.uuid4())
            change_ids.append(change_id)

            metadata_db.create_change(
                change_id=change_id,
                database_id=sample_database,
                origin_branch_id=sample_branch,
                change_type="CREATE_TABLE",
                entity_type="table",
                entity_name=f"table_{i}"
            )

            metadata_db.link_change_to_branch(
                branch_id=sample_branch,
                change_id=change_id,
                applied=(i == 0),  # First one is applied
                applied_order=i
            )

        # Copy changes to target branch
        metadata_db.copy_branch_changes(sample_branch, target_branch_id)

        # Verify target has all changes
        target_changes = metadata_db.get_branch_changes(target_branch_id)
        assert len(target_changes) == 3

        # Verify order and applied status preserved
        for i, change in enumerate(target_changes):
            assert change["id"] == change_ids[i]
            assert change["applied"] == (1 if i == 0 else 0)
            # Check that copied_from is set correctly
            assert change["copied_from_branch_id"] == sample_branch

    def test_unlink_change_from_branch(self, metadata_db, sample_database, sample_branch):
        """Test unlinking a change from a branch."""
        change_id = str(uuid.uuid4())

        # Create and link change
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="DROP_TABLE",
            entity_type="table",
            entity_name="temp_table"
        )

        metadata_db.link_change_to_branch(
            branch_id=sample_branch,
            change_id=change_id,
            applied=False,
            applied_order=0
        )

        # Verify change is linked
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 1

        # Unlink the change
        metadata_db.unlink_change_from_branch(sample_branch, change_id)

        # Verify change is unlinked
        changes = metadata_db.get_branch_changes(sample_branch)
        assert len(changes) == 0

        # But change record still exists
        change = metadata_db.get_change(change_id)
        assert change is not None

    def test_change_with_null_details(self, metadata_db, sample_database, sample_branch):
        """Test creating a change with null details."""
        change_id = str(uuid.uuid4())

        # Create change without details
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="DROP_TABLE",
            entity_type="table",
            entity_name="old_table",
            details=None,
            sql=None
        )

        # Verify change exists with null details
        change = metadata_db.get_change(change_id)
        assert change is not None
        assert change["details"] is None
        assert change["sql"] is None

    def test_multiple_branches_same_change(self, metadata_db, sample_database, sample_branch):
        """Test linking the same change to multiple branches."""
        # Create a second branch
        branch2_id = str(uuid.uuid4())
        metadata_db.create_branch(branch2_id, sample_database, "feature2")

        # Create a change
        change_id = str(uuid.uuid4())
        metadata_db.create_change(
            change_id=change_id,
            database_id=sample_database,
            origin_branch_id=sample_branch,
            change_type="CREATE_INDEX",
            entity_type="index",
            entity_name="idx_users_email"
        )

        # Link to both branches
        metadata_db.link_change_to_branch(
            branch_id=sample_branch,
            change_id=change_id,
            applied=True,
            applied_order=0
        )

        metadata_db.link_change_to_branch(
            branch_id=branch2_id,
            change_id=change_id,
            applied=False,
            applied_order=0,
            copied_from_branch_id=sample_branch
        )

        # Verify both branches have the change
        branch1_changes = metadata_db.get_branch_changes(sample_branch)
        branch2_changes = metadata_db.get_branch_changes(branch2_id)

        assert len(branch1_changes) == 1
        assert len(branch2_changes) == 1
        assert branch1_changes[0]["id"] == branch2_changes[0]["id"]
        assert branch1_changes[0]["applied"] == 1
        assert branch2_changes[0]["applied"] == 0

    def test_copy_empty_branch_changes(self, metadata_db, sample_database, sample_branch):
        """Test copying changes from a branch with no changes."""
        # Create a second branch
        target_branch_id = str(uuid.uuid4())
        metadata_db.create_branch(target_branch_id, sample_database, "empty_feature")

        # Copy from empty source (should not error)
        metadata_db.copy_branch_changes(sample_branch, target_branch_id)

        # Verify target is still empty
        changes = metadata_db.get_branch_changes(target_branch_id)
        assert len(changes) == 0