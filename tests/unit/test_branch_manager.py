"""Tests for BranchManager."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.managers.branch import BranchManager
from cinchdb.config import Config


class TestBranchManager:
    """Test branch management functionality."""
    
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
        branch_path = branch_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "feature"
        assert branch_path.exists()
        assert (branch_path / "metadata.json").exists()
        assert (branch_path / "changes.json").exists()
        assert (branch_path / "tenants").exists()
        
        # List branches should now show 2
        branches = branch_manager.list_branches()
        assert len(branches) == 2
        assert sorted([b.name for b in branches]) == ["feature", "main"]
    
    def test_create_branch_copies_tenants(self, branch_manager, temp_project):
        """Test that creating a branch copies all tenants."""
        # Create an additional tenant in main
        main_tenants = temp_project / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants"
        (main_tenants / "customer1.db").touch()
        
        # Create branch
        branch_manager.create_branch("main", "feature")
        
        # Check tenants were copied
        feature_tenants = temp_project / ".cinchdb" / "databases" / "main" / "branches" / "feature" / "tenants"
        assert (feature_tenants / "main.db").exists()
        assert (feature_tenants / "customer1.db").exists()
    
    def test_create_branch_duplicate_fails(self, branch_manager):
        """Test creating a branch with duplicate name fails."""
        branch_manager.create_branch("main", "feature")
        
        with pytest.raises(ValueError, match="Branch 'feature' already exists"):
            branch_manager.create_branch("main", "feature")
    
    def test_create_branch_from_nonexistent_fails(self, branch_manager):
        """Test creating a branch from non-existent source fails."""
        with pytest.raises(ValueError, match="Source branch 'nonexistent' does not exist"):
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
        feature_path = branch_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "feature"
        assert not feature_path.exists()
    
    def test_delete_main_branch_fails(self, branch_manager):
        """Test that deleting main branch fails."""
        with pytest.raises(ValueError, match="Cannot delete the main branch"):
            branch_manager.delete_branch("main")
    
    def test_delete_nonexistent_branch_fails(self, branch_manager):
        """Test deleting non-existent branch fails."""
        with pytest.raises(ValueError, match="Branch 'nonexistent' does not exist"):
            branch_manager.delete_branch("nonexistent")
    
    def test_switch_branch(self, branch_manager, temp_project):
        """Test switching active branch."""
        # Create a branch
        branch_manager.create_branch("main", "feature")
        
        # Switch to it
        branch_manager.switch_branch("feature")
        
        # Check config was updated
        config = Config(temp_project)
        project_config = config.load()
        assert project_config.active_branch == "feature"
    
    def test_switch_to_nonexistent_branch_fails(self, branch_manager):
        """Test switching to non-existent branch fails."""
        with pytest.raises(ValueError, match="Branch 'nonexistent' does not exist"):
            branch_manager.switch_branch("nonexistent")
    
    def test_get_branch_metadata(self, branch_manager):
        """Test getting branch metadata."""
        metadata = branch_manager.get_branch_metadata("main")
        
        assert "created_at" in metadata
        assert metadata["tables"] == {}
        assert metadata["views"] == {}
    
    def test_update_branch_metadata(self, branch_manager):
        """Test updating branch metadata."""
        # Get current metadata
        metadata = branch_manager.get_branch_metadata("main")
        
        # Update it
        metadata["tables"]["users"] = {
            "columns": ["id", "name", "email"]
        }
        
        branch_manager.update_branch_metadata("main", metadata)
        
        # Read it back
        updated = branch_manager.get_branch_metadata("main")
        assert "users" in updated["tables"]
        assert updated["tables"]["users"]["columns"] == ["id", "name", "email"]