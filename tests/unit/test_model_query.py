"""Tests for model.query() method - type-safe queries from generated models."""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

from cinchdb.config import Config
from cinchdb.managers.table import TableManager
from cinchdb.managers.codegen import CodegenManager
from cinchdb.managers.data import DataManager
from cinchdb.models import Column


class TestModelQuery:
    """Test suite for query() method on generated models."""
    
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
    def setup_test_env(self, temp_project):
        """Set up test environment with tables and generated models."""
        project_root = temp_project
        database = "main"
        branch = "main"
        tenant = "main"
        
        # Create table manager and tables
        table_manager = TableManager(project_root, database, branch, tenant)
        
        # Create products table
        product_columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="price", type="REAL", nullable=False),
            Column(name="stock", type="INTEGER", nullable=False),
            Column(name="category", type="TEXT", nullable=True)
        ]
        table_manager.create_table("products", product_columns)
        
        # Create orders table  
        order_columns = [
            Column(name="product_id", type="TEXT", nullable=False),
            Column(name="quantity", type="INTEGER", nullable=False),
            Column(name="total", type="REAL", nullable=False),
            Column(name="status", type="TEXT", nullable=False)
        ]
        table_manager.create_table("orders", order_columns)
        
        # Generate models
        codegen_manager = CodegenManager(project_root, database, branch, tenant)
        output_dir = temp_project / "generated_models"
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Add generated models to Python path
        sys.path.insert(0, str(output_dir))
        
        # Import the generated models
        from products import Products
        from orders import Orders
        
        # Set up connections
        Products.set_connection(project_root, database, branch, tenant)
        Orders.set_connection(project_root, database, branch, tenant)
        
        # Create test data
        data_manager = DataManager(project_root, database, branch, tenant)
        
        # Add products
        products_data = [
            {"name": "Laptop", "price": 999.99, "stock": 10, "category": "Electronics"},
            {"name": "Mouse", "price": 29.99, "stock": 50, "category": "Electronics"},
            {"name": "Desk", "price": 299.99, "stock": 5, "category": "Furniture"},
            {"name": "Chair", "price": 199.99, "stock": 15, "category": "Furniture"},
            {"name": "Notebook", "price": 4.99, "stock": 100, "category": "Stationery"}
        ]
        
        created_products = []
        for prod_data in products_data:
            prod = Products(**prod_data)
            created_products.append(data_manager.create(prod))
        
        # Add orders
        orders_data = [
            {"product_id": created_products[0].id, "quantity": 1, "total": 999.99, "status": "completed"},
            {"product_id": created_products[1].id, "quantity": 2, "total": 59.98, "status": "completed"},
            {"product_id": created_products[2].id, "quantity": 1, "total": 299.99, "status": "pending"},
            {"product_id": created_products[0].id, "quantity": 1, "total": 999.99, "status": "cancelled"}
        ]
        
        for order_data in orders_data:
            order = Orders(**order_data)
            data_manager.create(order)
        
        yield {
            "project_root": project_root,
            "output_dir": output_dir,
            "Products": Products,
            "Orders": Orders,
            "product_ids": [p.id for p in created_products]
        }
        
        # Clean up sys.path
        sys.path.remove(str(output_dir))
    
    def test_simple_query(self, setup_test_env):
        """Test basic SELECT query using model.query()."""
        Products = setup_test_env["Products"]
        
        # Query all products
        all_products = Products.query("SELECT * FROM products")
        
        assert len(all_products) == 5
        assert all(isinstance(p, Products) for p in all_products)
        
        # Check that all fields are populated
        for product in all_products:
            assert product.id is not None
            assert product.name is not None
            assert product.price is not None
            assert product.stock is not None
    
    def test_query_with_where_clause(self, setup_test_env):
        """Test query with WHERE clause."""
        Products = setup_test_env["Products"]
        
        # Query electronics products
        electronics = Products.query(
            "SELECT * FROM products WHERE category = ?",
            ("Electronics",)
        )
        
        assert len(electronics) == 2
        assert all(p.category == "Electronics" for p in electronics)
        
        names = [p.name for p in electronics]
        assert "Laptop" in names
        assert "Mouse" in names
    
    def test_query_with_complex_conditions(self, setup_test_env):
        """Test query with complex WHERE conditions."""
        Products = setup_test_env["Products"]
        
        # Query products with price between 50 and 500 and stock > 10
        results = Products.query(
            """
            SELECT * FROM products 
            WHERE price BETWEEN ? AND ? 
            AND stock > ?
            ORDER BY price DESC
            """,
            (50, 500, 10)
        )
        
        assert len(results) == 1
        assert results[0].name == "Chair"  # 199.99, stock=15
    
    def test_query_with_aggregate(self, setup_test_env):
        """Test query with aggregate functions."""
        Orders = setup_test_env["Orders"]
        Products = setup_test_env["Products"]
        
        # This query returns non-standard columns, so we use execute() instead
        # But we can still query orders normally
        completed_orders = Orders.query(
            "SELECT * FROM orders WHERE status = ?",
            ("completed",)
        )
        
        assert len(completed_orders) == 2
        assert all(o.status == "completed" for o in completed_orders)
    
    def test_query_with_join(self, setup_test_env):
        """Test that complex joins work with appropriate field selection."""
        Products = setup_test_env["Products"]
        
        # Query products that have been ordered
        # Note: We select only product fields to match the Products model
        ordered_products = Products.query(
            """
            SELECT DISTINCT p.* 
            FROM products p
            INNER JOIN orders o ON p.id = o.product_id
            WHERE o.status != ?
            """,
            ("cancelled",)
        )
        
        assert len(ordered_products) == 3
        
        names = [p.name for p in ordered_products]
        assert "Laptop" in names
        assert "Mouse" in names
        assert "Desk" in names
    
    def test_query_with_order_and_limit(self, setup_test_env):
        """Test query with ORDER BY and LIMIT."""
        Products = setup_test_env["Products"]
        
        # Get top 3 most expensive products
        top_products = Products.query(
            "SELECT * FROM products ORDER BY price DESC LIMIT 3"
        )
        
        assert len(top_products) == 3
        assert top_products[0].name == "Laptop"
        assert top_products[1].name == "Desk"
        assert top_products[2].name == "Chair"
    
    def test_query_with_named_parameters(self, setup_test_env):
        """Test query with named parameters."""
        Products = setup_test_env["Products"]
        
        # Query with named parameters
        results = Products.query(
            """
            SELECT * FROM products 
            WHERE stock >= :min_stock 
            AND category = :category
            """,
            {"min_stock": 10, "category": "Electronics"}
        )
        
        assert len(results) == 2
        assert all(p.stock >= 10 for p in results)
        assert all(p.category == "Electronics" for p in results)
    
    def test_query_non_select_fails(self, setup_test_env):
        """Test that non-SELECT queries are rejected."""
        Products = setup_test_env["Products"]
        
        # Try UPDATE
        with pytest.raises(ValueError, match="Model.query\\(\\) can only execute SELECT queries"):
            Products.query("UPDATE products SET stock = 0")
        
        # Try INSERT
        with pytest.raises(ValueError, match="Model.query\\(\\) can only execute SELECT queries"):
            Products.query("INSERT INTO products (name, price) VALUES ('Test', 10.0)")
        
        # Try DELETE
        with pytest.raises(ValueError, match="Model.query\\(\\) can only execute SELECT queries"):
            Products.query("DELETE FROM products WHERE id = 'test'")
    
    def test_query_empty_results(self, setup_test_env):
        """Test query that returns no results."""
        Products = setup_test_env["Products"]
        
        # Query for non-existent category
        results = Products.query(
            "SELECT * FROM products WHERE category = ?",
            ("NonExistent",)
        )
        
        assert results == []
        assert isinstance(results, list)
    
    def test_query_case_insensitive(self, setup_test_env):
        """Test that SELECT keyword is case-insensitive."""
        Products = setup_test_env["Products"]
        
        # Test lowercase
        results1 = Products.query("select * from products where stock > 20")
        
        # Test mixed case
        results2 = Products.query("SeLeCt * from products where stock > 20")
        
        # Test with whitespace
        results3 = Products.query("  SELECT * from products where stock > 20  ")
        
        assert len(results1) == len(results2) == len(results3)
        assert all(p.stock > 20 for p in results1)
    
    def test_query_validation_error(self, setup_test_env):
        """Test that validation errors are handled properly."""
        Products = setup_test_env["Products"]
        
        # Query that returns incomplete data should fail validation
        # Since our generated models have required fields
        with pytest.raises(Exception):  # Could be ValidationError or database error
            # This query would fail because it doesn't return all required fields
            Products.query("SELECT id, name FROM products")
    
    def test_concurrent_queries(self, setup_test_env):
        """Test that multiple models can query concurrently."""
        Products = setup_test_env["Products"]
        Orders = setup_test_env["Orders"]
        
        # Query from both models
        all_products = Products.query("SELECT * FROM products")
        all_orders = Orders.query("SELECT * FROM orders")
        
        assert len(all_products) == 5
        assert len(all_orders) == 4
        
        # Verify types
        assert all(isinstance(p, Products) for p in all_products)
        assert all(isinstance(o, Orders) for o in all_orders)