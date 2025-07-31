#!/usr/bin/env python3
"""
Remote API connection example.

This example demonstrates:
- Connecting to remote CinchDB API
- Performing operations over HTTP
- Error handling for remote connections
- Using both local and remote connections
"""

import cinchdb
from cinchdb.models import Column
import os
import time


def setup_remote_connection():
    """Set up connection to remote API."""
    # In production, use environment variables
    api_url = os.environ.get("CINCHDB_API_URL", "http://localhost:8000")
    api_key = os.environ.get("CINCHDB_API_KEY", "ck_test_example_key")
    
    print(f"Connecting to remote API: {api_url}")
    
    try:
        # Connect to remote API
        db = cinchdb.connect_api(
            api_url=api_url,
            api_key=api_key,
            database="remote_example",
            branch="main",
            tenant="main"
        )
        
        print("✓ Connected to remote API")
        return db
    
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nTo run this example:")
        print("1. Get your Cinch API Key and Database URL")
        print("2. Set environment variables:")
        print("   export CINCHDB_API_URL=http://localhost:8000")
        print("   export CINCHDB_API_KEY=<your-api-key>")
        return None


def demonstrate_remote_operations(db):
    """Show various remote operations."""
    print("\n--- Remote Operations Demo ---")
    
    # Create table
    print("\nCreating table via API...")
    try:
        db.create_table("remote_data", [
            Column(name="key", type="TEXT"),
            Column(name="value", type="TEXT"),
            Column(name="timestamp", type="TEXT")
        ])
        print("✓ Table created")
    except Exception as e:
        print(f"Table might already exist: {e}")
    
    # Insert data
    print("\nInserting data via API...")
    for i in range(3):
        record = db.insert("remote_data", {
            "key": f"key_{i}",
            "value": f"value_{i}",
            "timestamp": time.time()
        })
        print(f"✓ Inserted: {record['key']}")
    
    # Query data
    print("\nQuerying data via API...")
    results = db.query("SELECT * FROM remote_data ORDER BY key")
    for row in results:
        print(f"  {row['key']}: {row['value']}")
    
    # Update data
    print("\nUpdating data via API...")
    if results:
        first_record = results[0]
        updated = db.update("remote_data", first_record["id"], {
            "value": "updated_value",
            "timestamp": time.time()
        })
        print(f"✓ Updated: {updated['key']}")
    
    # Complex query
    print("\nExecuting complex query via API...")
    stats = db.query("""
        SELECT 
            COUNT(*) as total,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest
        FROM remote_data
    """)[0]
    
    print(f"  Total records: {stats['total']}")
    print(f"  Time range: {stats['latest'] - stats['earliest']:.2f} seconds")


def demonstrate_error_handling(db):
    """Show error handling for remote operations."""
    print("\n--- Error Handling Demo ---")
    
    # Try to query non-existent table
    print("\nQuerying non-existent table...")
    try:
        db.query("SELECT * FROM does_not_exist")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Try invalid SQL
    print("\nExecuting invalid SQL...")
    try:
        db.query("INVALID SQL STATEMENT")
    except Exception as e:
        print(f"✓ Caught expected error: {e}")
    
    # Try to create duplicate table
    print("\nCreating duplicate table...")
    try:
        db.create_table("remote_data", [
            Column(name="test", type="TEXT")
        ])
    except Exception as e:
        print(f"✓ Caught expected error: {e}")


def demonstrate_remote_vs_local():
    """Compare remote and local operations."""
    print("\n--- Remote vs Local Comparison ---")
    
    # Local connection
    print("\nLocal connection:")
    local_db = cinchdb.connect("comparison_example")
    print(f"  Is local: {local_db.is_local}")
    print(f"  Project dir: {local_db.project_dir}")
    
    # Measure local performance
    start = time.time()
    for i in range(10):
        local_db.query("SELECT 1")
    local_time = time.time() - start
    print(f"  10 queries: {local_time:.3f} seconds")
    
    # Remote connection (if available)
    remote_db = setup_remote_connection()
    if remote_db:
        print("\nRemote connection:")
        print(f"  Is local: {remote_db.is_local}")
        print(f"  API URL: {remote_db.api_url}")
        
        # Measure remote performance
        start = time.time()
        for i in range(10):
            remote_db.query("SELECT 1")
        remote_time = time.time() - start
        print(f"  10 queries: {remote_time:.3f} seconds")
        
        print(f"\nLatency difference: {(remote_time - local_time) * 100:.1f} ms per query")


def demonstrate_connection_pooling():
    """Show connection pooling benefits."""
    print("\n--- Connection Pooling Demo ---")
    
    # Create multiple connections
    connections = []
    
    print("Creating multiple remote connections...")
    for i in range(3):
        db = setup_remote_connection()
        if db:
            connections.append(db)
            print(f"  Connection {i+1} created")
    
    if connections:
        # Use connections concurrently
        print("\nUsing connections concurrently...")
        import concurrent.futures
        
        def query_with_connection(conn_idx):
            conn = connections[conn_idx]
            result = conn.query("SELECT ? as conn_id", [conn_idx])
            return result[0]["conn_id"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(query_with_connection, i) for i in range(len(connections))]
            results = [f.result() for f in futures]
            
        print(f"  Results from parallel queries: {results}")
        
        # Clean up
        for conn in connections:
            conn.close()


def main():
    print("Remote API Connection Example")
    print("=" * 50)
    
    # Try to connect to remote API
    db = setup_remote_connection()
    
    if db:
        # Demonstrate remote operations
        demonstrate_remote_operations(db)
        demonstrate_error_handling(db)
        
        # Close connection
        db.close()
    
    # Compare with local
    demonstrate_remote_vs_local()
    
    # Show connection pooling
    # demonstrate_connection_pooling()
    
    print("\nExample completed!")
    
    if not db:
        print("\nNote: To see remote operations, start the API server first.")


if __name__ == "__main__":
    main()