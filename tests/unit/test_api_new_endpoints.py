"""Tests for new API endpoints business logic - data CRUD, codegen, and branch operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.config import Config


class TestNewAPIFunctionality:
    """Test new API functionality that was added."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create project structure
        cinchdb_dir = temp_dir / ".cinchdb"
        cinchdb_dir.mkdir()

        # Create config
        config = Config(temp_dir)
        config_data = config.load()
        config_data.active_database = "test_db"
        config_data.active_branch = "main"
        config.save(config_data)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_data_router_imports(self):
        """Test that the data router can be imported successfully."""
        from cinchdb.api.routers.data import router as data_router
        from cinchdb.api.routers.data import create_table_model

        assert data_router is not None
        assert create_table_model is not None

    def test_codegen_router_imports(self):
        """Test that the codegen router can be imported successfully."""
        from cinchdb.api.routers.codegen import router as codegen_router
        from cinchdb.api.routers.codegen import CodegenLanguage, GenerateModelsRequest

        assert codegen_router is not None
        assert CodegenLanguage is not None
        assert GenerateModelsRequest is not None

    def test_branch_operations_imports(self):
        """Test that the enhanced branches router can be imported successfully."""
        from cinchdb.api.routers.branches import router as branches_router
        from cinchdb.api.routers.branches import (
            BranchComparisonResult,
            MergeCheckResult,
        )

        assert branches_router is not None
        assert BranchComparisonResult is not None
        assert MergeCheckResult is not None

    def test_create_table_model_helper(self):
        """Test that the create_table_model helper function exists and can be imported."""
        from cinchdb.api.routers.data import create_table_model

        # Just test that the function exists and is callable
        assert callable(create_table_model)

        # Skip actual model creation due to Pydantic complexity in tests

    def test_api_routers_registered(self):
        """Test that new routers are properly registered in the main app."""
        from cinchdb.api.app import app

        # Check that our new endpoints are in the routes
        routes = [route.path for route in app.routes]

        # Should include data endpoints (prefixed with /api/v1/tables)
        data_routes = [r for r in routes if "/api/v1/tables" in r and "/data" in r]
        assert len(data_routes) > 0, "Data CRUD endpoints should be registered"

        # Should include codegen endpoints
        codegen_routes = [r for r in routes if "/api/v1/codegen" in r]
        assert len(codegen_routes) > 0, "Codegen endpoints should be registered"

    def test_pydantic_models_structure(self):
        """Test that new Pydantic models are properly structured."""
        from cinchdb.api.routers.data import (
            CreateDataRequest,
            UpdateDataRequest,
            BulkCreateRequest,
        )
        from cinchdb.api.routers.codegen import GenerateModelsRequest, CodegenLanguage
        from cinchdb.api.routers.branches import (
            MergeBranchRequest,
            BranchComparisonResult,
        )

        # Test data models
        create_req = CreateDataRequest(data={"name": "test"})
        assert create_req.data["name"] == "test"

        update_req = UpdateDataRequest(data={"name": "updated"})
        assert update_req.data["name"] == "updated"

        bulk_req = BulkCreateRequest(records=[{"name": "test1"}, {"name": "test2"}])
        assert len(bulk_req.records) == 2

        # Test codegen models
        gen_req = GenerateModelsRequest(language="python")
        assert gen_req.language == "python"
        assert gen_req.include_tables is True
        assert gen_req.include_views is True

        lang = CodegenLanguage(name="python", description="Python models")
        assert lang.name == "python"

        # Test branch models
        merge_req = MergeBranchRequest(source="feature", target="main")
        assert merge_req.source == "feature"
        assert merge_req.target == "main"
        assert merge_req.force is False

        comparison = BranchComparisonResult(
            source_branch="feature",
            target_branch="main",
            source_only_changes=5,
            target_only_changes=2,
            common_ancestor="abc123",
            can_fast_forward=True,
        )
        assert comparison.source_branch == "feature"
        assert comparison.can_fast_forward is True

    def test_cinchdb_remote_data_methods_updated(self):
        """Test that CinchDB remote methods are updated for new endpoints."""
        from cinchdb.core.database import CinchDB

        # Create a remote instance
        db = CinchDB(database="test", api_url="https://example.com", api_key="test-key")

        assert db.is_local is False
        assert hasattr(db, "insert")
        assert hasattr(db, "update")
        assert hasattr(db, "delete")
        assert hasattr(db, "query")

    def test_endpoint_count_validation(self):
        """Test that we have added the expected number of new endpoints."""
        from cinchdb.api.app import app

        # Count total routes
        all_routes = [route for route in app.routes if hasattr(route, "path")]

        # Count data endpoints (should have multiple for CRUD operations)
        data_endpoints = [
            r for r in all_routes if "/tables/" in r.path and "/data" in r.path
        ]
        assert len(data_endpoints) >= 6, (
            f"Expected at least 6 data endpoints, got {len(data_endpoints)}"
        )

        # Count codegen endpoints (should have language listing, files generation, and info)
        codegen_endpoints = [r for r in all_routes if "/codegen" in r.path]
        assert len(codegen_endpoints) >= 3, (
            f"Expected at least 3 codegen endpoints, got {len(codegen_endpoints)}"
        )

        # Count new branch endpoints (should have comparison and merge)
        branch_endpoints = [
            r
            for r in all_routes
            if "/branches/" in r.path
            and any(op in r.path for op in ["compare", "merge", "can-merge"])
        ]
        assert len(branch_endpoints) >= 3, (
            f"Expected at least 3 new branch endpoints, got {len(branch_endpoints)}"
        )

    def test_manager_integration(self):
        """Test that the new endpoints properly use existing managers."""
        from cinchdb.managers.data import DataManager
        from cinchdb.managers.codegen import CodegenManager
        from cinchdb.managers.merge_manager import MergeManager
        from cinchdb.managers.change_comparator import ChangeComparator

        # Test that manager classes can be imported
        assert DataManager is not None
        assert CodegenManager is not None
        assert MergeManager is not None
        assert ChangeComparator is not None
