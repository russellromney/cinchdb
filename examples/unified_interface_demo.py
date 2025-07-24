"""Example demonstrating the unified CinchDB interface.

This example shows how to use the new unified interface for both
local and remote connections, as well as the traditional manager pattern.
"""



def main():
    """Demonstrate various ways to use CinchDB."""
    
    print("=== CinchDB Unified Interface Demo ===\n")
    
    # Example 1: Simple local connection
    print("1. Simple local connection:")
    print("   db = cinchdb.connect('mydb')")
    print("   results = db.query('SELECT * FROM users')")
    print("   db.create_table('products', columns)")
    
    # Example 2: Local connection with branch
    print("\n2. Local connection with specific branch:")
    print("   db = cinchdb.connect('mydb', branch='feature-branch')")
    print("   db.insert('users', {'name': 'Alice', 'email': 'alice@example.com'})")
    
    # Example 3: Remote API connection
    print("\n3. Remote API connection:")
    print("   db = cinchdb.connect_api(")
    print("       'https://api.cinchdb.com',")
    print("       'your-api-key',")
    print("       'mydb'")
    print("   )")
    print("   results = db.query('SELECT * FROM orders')")
    
    # Example 4: Using manager pattern (local only)
    print("\n4. Advanced operations with managers (local only):")
    print("   db = cinchdb.connect('mydb')")
    print("   if db.is_local:")
    print("       # Access managers for advanced operations")
    print("       db.tables.copy_table('users', 'users_backup')")
    print("       db.columns.rename_column('products', 'desc', 'description')")
    print("       db.branches.create_branch('main', 'dev')")
    
    # Example 5: Switching contexts
    print("\n5. Switching branches and tenants:")
    print("   db = cinchdb.connect('mydb', branch='main')")
    print("   ")
    print("   # Switch to development branch")
    print("   dev_db = db.switch_branch('dev')")
    print("   ")
    print("   # Switch to customer tenant")
    print("   customer_db = db.switch_tenant('customer1')")
    
    # Example 6: Context manager usage
    print("\n6. Using context manager (automatically closes connections):")
    print("   with cinchdb.connect_api(url, key, 'mydb') as db:")
    print("       results = db.query('SELECT COUNT(*) FROM users')")
    print("       # Connection automatically closed on exit")
    
    # Example 7: Creating tables with the unified interface
    print("\n7. Table creation example:")
    print("""
    columns = [
        Column(name='name', type='TEXT', nullable=False),
        Column(name='email', type='TEXT', nullable=False),
        Column(name='age', type='INTEGER', nullable=True),
        Column(name='active', type='BOOLEAN', default=True)
    ]
    
    db.create_table('customers', columns)
    """)
    
    # Example 8: CRUD operations
    print("\n8. CRUD operations:")
    print("""
    # Insert
    customer = db.insert('customers', {
        'name': 'Bob Smith',
        'email': 'bob@example.com',
        'age': 30
    })
    
    # Update
    db.update('customers', customer['id'], {'age': 31})
    
    # Query
    results = db.query(
        'SELECT * FROM customers WHERE age > ?',
        [25]
    )
    
    # Delete
    db.delete('customers', customer['id'])
    """)
    
    print("\n=== Migration Guide ===")
    print("\nMigrating from manager pattern to unified interface:")
    print("\nOld way:")
    print("""
    from cinchdb.managers.table import TableManager
    from cinchdb.managers.query import QueryManager
    
    table_mgr = TableManager(project_dir, 'mydb', 'main', 'main')
    query_mgr = QueryManager(project_dir, 'mydb', 'main', 'main')
    
    table_mgr.create_table('users', columns)
    results = query_mgr.execute('SELECT * FROM users')
    """)
    
    print("\nNew way:")
    print("""
    import cinchdb
    
    db = cinchdb.connect('mydb')
    db.create_table('users', columns)
    results = db.query('SELECT * FROM users')
    
    # Or use managers if needed:
    db.tables.create_table('users', columns)
    """)
    
    print("\n=== Key Benefits ===")
    print("- Simpler API for common operations")
    print("- Single object to manage all database operations")
    print("- Same interface for local and remote connections")
    print("- Backward compatible - managers still accessible")
    print("- Lazy loading - only loads what you use")
    print("- Context manager support for proper cleanup")


if __name__ == "__main__":
    main()