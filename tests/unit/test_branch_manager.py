"""Tests for BranchManager."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.managers.branch import BranchManager


class TestBranchManager:
    """Test branch management functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project with proper database and branch setup
        from cinchdb.core.initializer import ProjectInitializer
        initializer = ProjectInitializer(project_dir)
        initializer.init_project(database_name="main", branch_name="main")

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def branch_manager(self, temp_project):
        """Create a BranchManager instance."""
        return BranchManager(temp_project, "main")

    def test_list_branches_initial(self, branch_manager):
        """Test listing branches in a new project."""
        branches = branch_manager.list_branches()

        assert len(branches) == 1
        assert branches[0].name == "main"
        assert branches[0].is_main
        assert branches[0].database == "main"

    def test_create_branch(self, branch_manager):
        """Test creating a new branch."""
        # Create a branch from main
        new_branch = branch_manager.create_branch("main", "feature")

        assert new_branch.name == "feature"
        assert new_branch.parent_branch == "main"
        assert new_branch.database == "main"
        assert not new_branch.is_main

        # Verify directory structure was created
        branch_path = (
            branch_manager.project_root
            / ".cinchdb"
            / "databases"
            / "main"
            / "branches"
            / "feature"
        )
        assert branch_path.exists()
        assert (branch_path / "metadata.json").exists()
        assert (branch_path / "changes.json").exists()
        assert (branch_path / "tenants").exists()

        # List branches should now show 2
        branches = branch_manager.list_branches()
        assert len(branches) == 2
        assert sorted([b.name for b in branches]) == ["feature", "main"]

    def test_create_branch_copies_tenants(self, branch_manager, temp_project):
        """Test that creating a branch copies all tenant metadata."""
        # Create an additional materialized tenant in main branch using TenantManager
        from cinchdb.managers.tenant import TenantManager
        main_tenant_mgr = TenantManager(temp_project, "main", "main")
        main_tenant_mgr.create_tenant("customer1", lazy=False)

        # Create branch
        branch_manager.create_branch("main", "feature")

        # Check tenant metadata was copied (tenants will be lazy in new branch)
        feature_tenant_mgr = TenantManager(temp_project, "main", "feature")
        feature_tenants = feature_tenant_mgr.list_tenants()
        tenant_names = [t.name for t in feature_tenants if not t.name.startswith("__")]
        
        # Should have copied both main and customer1 tenants (as lazy)
        assert "main" in tenant_names
        assert "customer1" in tenant_names

    def test_create_branch_duplicate_fails(self, branch_manager):
        """Test creating a branch with duplicate name fails."""
        branch_manager.create_branch("main", "feature")

        with pytest.raises(ValueError, match="Branch 'feature' already exists"):
            branch_manager.create_branch("main", "feature")

    def test_create_branch_from_nonexistent_fails(self, branch_manager):
        """Test creating a branch from non-existent source fails."""
        with pytest.raises(
            ValueError, match="Source branch 'nonexistent' does not exist"
        ):
            branch_manager.create_branch("nonexistent", "feature")

    def test_delete_branch(self, branch_manager):
        """Test deleting a branch."""
        # Create a branch first
        branch_manager.create_branch("main", "feature")
        assert len(branch_manager.list_branches()) == 2

        # Delete it
        branch_manager.delete_branch("feature")

        # Should be gone
        branches = branch_manager.list_branches()
        assert len(branches) == 1
        assert branches[0].name == "main"

        # Directory should be gone
        feature_path = (
            branch_manager.project_root
            / ".cinchdb"
            / "databases"
            / "main"
            / "branches"
            / "feature"
        )
        assert not feature_path.exists()

    def test_delete_main_branch_fails(self, branch_manager):
        """Test that deleting main branch fails."""
        with pytest.raises(ValueError, match="Cannot delete the main branch"):
            branch_manager.delete_branch("main")

    def test_delete_nonexistent_branch_fails(self, branch_manager):
        """Test deleting non-existent branch fails."""
        with pytest.raises(ValueError, match="Branch 'nonexistent' does not exist"):
            branch_manager.delete_branch("nonexistent")

    def test_get_branch_metadata(self, branch_manager):
        """Test getting branch metadata."""
        metadata = branch_manager.get_branch_metadata("main")

        assert "created_at" in metadata

    def test_update_branch_metadata(self, branch_manager):
        """Test updating branch metadata."""
        # Get current metadata
        metadata = branch_manager.get_branch_metadata("main")

        # Update it with custom field
        metadata["custom_field"] = "custom_value"

        branch_manager.update_branch_metadata("main", metadata)

        # Read it back
        updated = branch_manager.get_branch_metadata("main")
        assert updated["custom_field"] == "custom_value"
