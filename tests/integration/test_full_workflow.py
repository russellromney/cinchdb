"""Integration tests for full CinchDB workflows."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.column import ColumnManager
from cinchdb.managers.view import ViewModel
from cinchdb.managers.merge_manager import MergeManager
from cinchdb.models import Column


class TestFullWorkflow:
    """Test complete CinchDB workflows."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Initialize project
        init_project(project_path)

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_complete_database_workflow(self, temp_project):
        """Test a complete database workflow from creation to merge."""
        # Step 1: Create a feature branch
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Step 2: Create tables in feature branch
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="main"))

        # Create users table
        users_table = table_mgr.create_table(
            "users",
            [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="email", type="TEXT", unique=True),
            ],
        )
        assert users_table.name == "users"
        assert len(users_table.columns) == 5  # id, created_at, updated_at, name, email

        # Create posts table
        posts_table = table_mgr.create_table(
            "posts",
            [
                Column(name="title", type="TEXT", nullable=False),
                Column(name="content", type="TEXT"),
                Column(name="user_id", type="TEXT", nullable=False),
            ],
        )
        assert posts_table.name == "posts"

        # Step 3: Add columns
        column_mgr = ColumnManager(ConnectionContext(project_root=temp_project, database="main", branch="feature"))
        column_mgr.add_column("users", Column(name="age", type="INTEGER"))

        # Verify column was added
        columns = column_mgr.list_columns("users")
        column_names = [col.name for col in columns]
        assert "age" in column_names

        # Step 4: Create views
        view_mgr = ViewModel(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="main"))
        view_mgr.create_view(
            "user_posts",
            """
            SELECT u.name, u.email, p.title, p.content
            FROM users u
            JOIN posts p ON u.id = p.user_id
        """,
        )

        views = view_mgr.list_views()
        assert len(views) == 1
        assert views[0].name == "user_posts"

        # Step 5: Create additional eager tenant
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="feature"))
        tenant_mgr.create_tenant("test-tenant", lazy=False)

        tenants = tenant_mgr.list_tenants()
        tenant_names = [t.name for t in tenants]
        assert "main" in tenant_names
        assert "test-tenant" in tenant_names

        # Step 6: Verify schema was copied to new tenant
        test_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="test-tenant"))
        test_tables = test_table_mgr.list_tables()
        table_names = [t.name for t in test_tables]
        assert "users" in table_names
        assert "posts" in table_names

        # Step 7: Merge feature branch into main
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        # Check merge preview first
        preview = merge_mgr.get_merge_preview("feature", "main")
        assert preview["can_merge"]
        assert preview["changes_to_merge"] > 0

        # Perform merge into main
        result = merge_mgr.merge_branches("feature", "main")
        assert result["success"]
        assert result["changes_merged"] > 0

        # Step 8: Verify changes are in main branch
        main_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        main_tables = main_table_mgr.list_tables()
        main_table_names = [t.name for t in main_tables]
        assert "users" in main_table_names
        assert "posts" in main_table_names

        main_column_mgr = ColumnManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        main_columns = main_column_mgr.list_columns("users")
        main_column_names = [col.name for col in main_columns]
        assert "age" in main_column_names

        main_view_mgr = ViewModel(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        main_views = main_view_mgr.list_views()
        assert len(main_views) == 1
        assert main_views[0].name == "user_posts"

    def test_multi_branch_development(self, temp_project):
        """Test development across multiple feature branches."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        # Create first feature branch
        branch_mgr.create_branch("main", "feature_users")

        # Create users table in feature branch
        users_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature_users", tenant="main"))
        users_table_mgr.create_table(
            "users",
            [
                Column(name="username", type="TEXT", unique=True, nullable=False),
                Column(name="email", type="TEXT", unique=True, nullable=False),
            ],
        )

        # Merge users feature first
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        users_result = merge_mgr.merge_branches("feature_users", "main")
        assert users_result["success"]

        # Create second feature branch from updated main
        branch_mgr.create_branch("main", "feature_products")

        # Develop products feature
        products_table_mgr = TableManager(
            ConnectionContext(project_root=temp_project, database="main", branch="feature_products", tenant="main")
        )
        products_table_mgr.create_table(
            "products",
            [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="price", type="REAL", nullable=False),
            ],
        )

        # Merge products feature
        products_result = merge_mgr.merge_branches("feature_products", "main")
        assert products_result["success"]

        # Verify both features are in main
        main_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        main_tables = main_table_mgr.list_tables()
        main_table_names = [t.name for t in main_tables]
        assert "users" in main_table_names
        assert "products" in main_table_names

    def test_tenant_isolation(self, temp_project):
        """Test that tenants are properly isolated."""
        # Create feature branch
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Create table in feature branch
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="main"))
        table_mgr.create_table(
            "items", [Column(name="name", type="TEXT", nullable=False)]
        )

        # Create additional eager tenants
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="feature"))
        tenant_mgr.create_tenant("tenant-a", lazy=False)
        tenant_mgr.create_tenant("tenant-b", lazy=False)

        # Verify all tenants have the table structure
        for tenant in ["main", "tenant-a", "tenant-b"]:
            tenant_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant=tenant))
            tables = tenant_table_mgr.list_tables()
            table_names = [t.name for t in tables]
            assert "items" in table_names

        # Add column - should apply to all tenants
        column_mgr = ColumnManager(ConnectionContext(project_root=temp_project, database="main", branch="feature"))
        column_mgr.add_column("items", Column(name="description", type="TEXT"))

        # Verify column exists in all tenants
        for tenant in ["main", "tenant-a", "tenant-b"]:
            tenant_column_mgr = ColumnManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant=tenant))
            columns = tenant_column_mgr.list_columns("items")
            column_names = [col.name for col in columns]
            assert "description" in column_names

        # Merge to main
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_branches("feature", "main")
        assert result["success"]

        # Verify structure exists in all tenants in main
        main_tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        main_tenants = main_tenant_mgr.list_tenants()

        for tenant in main_tenants:
            tenant_table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant=tenant.name))
            tables = tenant_table_mgr.list_tables()
            table_names = [t.name for t in tables]
            assert "items" in table_names

            tenant_column_mgr = ColumnManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant=tenant.name))
            columns = tenant_column_mgr.list_columns("items")
            column_names = [col.name for col in columns]
            assert "description" in column_names
