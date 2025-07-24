#!/usr/bin/env python3
"""
Demo script showing type-annotated SDK operations with CinchDB.

This example demonstrates:
1. Setting up a CinchDB project
2. Creating tables with the existing TableManager
3. Generating typed models with CRUD operations
4. Using the generated models for type-safe database operations
"""

import tempfile
from pathlib import Path
from cinchdb.config import Config
from cinchdb.managers.table import TableManager
from cinchdb.managers.codegen import CodegenManager
from cinchdb.models import Column
import sys


def main():
    """Run the SDK operations demo."""
    print("🚀 CinchDB Type-Annotated SDK Operations Demo")
    print("=" * 50)
    
    # Create a temporary project for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        database = "main" 
        branch = "main"
        tenant = "main"
        
        print(f"📁 Created temporary project at: {project_root}")
        
        # 1. Initialize the CinchDB project
        print("\n1️⃣ Initializing CinchDB project...")
        config = Config(project_root)
        config.init_project()
        print("✅ Project initialized")
        
        # 2. Create tables using the existing TableManager
        print("\n2️⃣ Creating database tables...")
        table_manager = TableManager(project_root, database, branch, tenant)
        
        # Create a users table
        user_columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False),
            Column(name="age", type="INTEGER", nullable=False),
            Column(name="active", type="INTEGER", nullable=True)  # boolean as integer
        ]
        table_manager.create_table("users", user_columns)
        
        # Create a posts table
        post_columns = [
            Column(name="title", type="TEXT", nullable=False),
            Column(name="content", type="TEXT", nullable=True),
            Column(name="published", type="INTEGER", nullable=False)  # boolean as integer
        ]
        table_manager.create_table("posts", post_columns)
        
        print("✅ Created 'users' and 'posts' tables")
        
        # 3. Generate typed models with CRUD operations
        print("\n3️⃣ Generating type-annotated models...")
        codegen_manager = CodegenManager(project_root, database, branch, tenant)
        output_dir = project_root / "generated_models"
        
        result = codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        print(f"✅ Generated {len(result['files_generated'])} files:")
        for file in result['files_generated']:
            print(f"   - {file}")
        
        # 4. Import and use the generated models
        print("\n4️⃣ Importing generated models...")
        sys.path.insert(0, str(output_dir))
        
        try:
            # Import the generated models
            from users import Users
            from posts import Posts
            
            print("✅ Imported Users and Posts models")
            
            # Set up database connections for the models
            Users.set_connection(project_root, database, branch, tenant)
            Posts.set_connection(project_root, database, branch, tenant)
            
            print("\n5️⃣ Demonstrating type-annotated CRUD operations...")
            
            # CREATE operations
            print("\n📝 Creating users...")
            user1 = Users.create(name="Alice Smith", email="alice@example.com", age=30, active=1)
            user2 = Users.create(name="Bob Johnson", email="bob@example.com", age=25)
            user3 = Users.create(name="Carol Davis", email="carol@example.com", age=35, active=1)
            
            print(f"   Created user: {user1.name} (ID: {user1.id[:8]}...)")
            print(f"   Created user: {user2.name} (ID: {user2.id[:8]}...)")
            print(f"   Created user: {user3.name} (ID: {user3.id[:8]}...)")
            
            # BULK CREATE
            print("\n📦 Bulk creating posts...")
            post_data = [
                {"title": "Getting Started with CinchDB", "content": "Learn the basics...", "published": 1},
                {"title": "Advanced Queries", "content": "Deep dive into...", "published": 1},
                {"title": "Draft Post", "content": "Work in progress...", "published": 0}
            ]
            posts = Posts.bulk_create(post_data)
            print(f"   Created {len(posts)} posts")
            
            # SELECT operations
            print("\n🔍 Querying data...")
            
            # Select all users
            all_users = Users.select()
            print(f"   Total users: {len(all_users)}")
            
            # Select with filters
            active_users = Users.select(active=1)
            print(f"   Active users: {len(active_users)}")
            
            # Select with operators
            young_users = Users.select(age__lt=30)
            print(f"   Users under 30: {len(young_users)}")
            
            # Find by ID
            found_user = Users.find_by_id(user1.id)
            print(f"   Found user by ID: {found_user.name}")
            
            # COUNT operations
            print(f"   User count: {Users.count()}")
            print(f"   Published posts: {Posts.count(published=1)}")
            
            # UPDATE operations
            print("\n✏️  Updating data...")
            user1.age = 31
            updated_user = user1.save()  # Upsert operation
            print(f"   Updated {updated_user.name}'s age to {updated_user.age}")
            
            # Explicit update
            user2.name = "Robert Johnson"
            user2.update()
            print(f"   Updated user name to {user2.name}")
            
            # DELETE operations
            print("\n🗑️  Deleting data...")
            
            # Delete by filters
            deleted_count = Posts.delete_records(published=0)
            print(f"   Deleted {deleted_count} unpublished posts")
            
            # Delete instance
            was_deleted = user3.delete()
            print(f"   Deleted user Carol: {was_deleted}")
            
            # Final counts
            print("\n📊 Final counts:")
            print(f"   Remaining users: {Users.count()}")
            print(f"   Remaining posts: {Posts.count()}")
            
            print("\n🎉 Demo completed successfully!")
            print("\nKey Benefits Demonstrated:")
            print("✨ Type-safe model creation and validation")
            print("✨ Intuitive CRUD operations (create, select, save, update, delete)")
            print("✨ Powerful filtering with operators (age__lt, age__gte, etc.)")
            print("✨ Bulk operations for performance")
            print("✨ Automatic ID and timestamp management")
            print("✨ Connection management per model class")
            
        except ImportError as e:
            print(f"❌ Failed to import generated models: {e}")
        except Exception as e:
            print(f"❌ Error during demo: {e}")
        finally:
            # Clean up sys.path
            if str(output_dir) in sys.path:
                sys.path.remove(str(output_dir))


if __name__ == "__main__":
    main()