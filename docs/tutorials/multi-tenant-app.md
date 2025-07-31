# Building a Multi-Tenant SaaS Application

Learn how to build a multi-tenant SaaS application with CinchDB.

## Overview

We'll build a project management SaaS where each customer has isolated data but shares the same schema.

## Initial Setup

### 1. Initialize Project
```bash
cinch init project_manager
cd project_manager
```

### 2. Create Schema
```bash
# Create tables on a feature branch
cinch branch create initial-schema
cinch branch switch initial-schema

# Users table
cinch table create users \
  email:TEXT \
  name:TEXT \
  role:TEXT \
  active:BOOLEAN

# Projects table  
cinch table create projects \
  name:TEXT \
  description:TEXT? \
  owner_id:TEXT \
  status:TEXT

# Tasks table
cinch table create tasks \
  project_id:TEXT \
  title:TEXT \
  description:TEXT? \
  assignee_id:TEXT? \
  status:TEXT \
  priority:TEXT

# Merge to main
cinch branch merge-into-main
```

## Customer Onboarding

### CLI Approach
```bash
# Create tenant for new customer
cinch tenant create acme_corp

# Add initial admin user
cinch query "INSERT INTO users (email, name, role, active) \
  VALUES ('admin@acme.com', 'ACME Admin', 'admin', true)" \
  --tenant acme_corp
```

### Python SDK Approach
```python
import cinchdb
from datetime import datetime

class CustomerOnboarding:
    def __init__(self, db_name="project_manager"):
        self.db = cinchdb.connect(db_name)
    
    def create_customer(self, company_name: str, admin_email: str):
        """Onboard a new customer."""
        # Create tenant
        tenant_name = company_name.lower().replace(" ", "_")
        if self.db.is_local:
            self.db.tenants.create_tenant(tenant_name)
        
        # Create new connection for tenant
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)
        
        # Create admin user
        admin = tenant_db.insert("users", {
            "email": admin_email,
            "name": f"{company_name} Admin",
            "role": "admin",
            "active": True
        })
        
        # Create welcome project
        project = tenant_db.insert("projects", {
            "name": "Getting Started",
            "description": "Welcome to ProjectManager!",
            "owner_id": admin["id"],
            "status": "active"
        })
        
        # Add sample tasks
        tasks = [
            "Invite team members",
            "Create your first project",
            "Customize settings"
        ]
        
        for i, task in enumerate(tasks):
            tenant_db.insert("tasks", {
                "project_id": project["id"],
                "title": task,
                "assignee_id": admin["id"],
                "status": "todo",
                "priority": "medium"
            })
        
        return {
            "tenant": tenant_name,
            "admin_id": admin["id"],
            "project_id": project["id"]
        }

# Usage
onboarding = CustomerOnboarding()
result = onboarding.create_customer("ACME Corp", "admin@acme.com")
print(f"Created tenant: {result['tenant']}")
```

## Multi-Tenant API

### FastAPI Application
```python
from fastapi import FastAPI, HTTPException, Depends
from typing import Optional
import cinchdb

app = FastAPI()

# Database connection
def get_db():
    return cinchdb.connect("project_manager")

# Tenant from header
def get_tenant(tenant: str = Header(...)):
    return tenant

# User authentication (simplified)
def get_current_user(token: str = Header(...)):
    # Validate token and return user
    return {"id": "user-123", "tenant": "acme_corp"}

@app.get("/projects")
def list_projects(
    tenant: str = Depends(get_tenant),
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    # Validate tenant access
    if user["tenant"] != tenant:
        raise HTTPException(403, "Access denied")
    
    # Query tenant data
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    projects = tenant_db.query(
        "SELECT * FROM projects WHERE owner_id = ?",
        [user["id"]]
    )
    
    return {"projects": projects}

@app.post("/projects")
def create_project(
    project: dict,
    tenant: str = Depends(get_tenant),
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    
    new_project = tenant_db.insert("projects", {
        **project,
        "owner_id": user["id"],
        "status": "active"
    })
    
    return new_project

@app.get("/tasks/{project_id}")
def list_tasks(
    project_id: str,
    tenant: str = Depends(get_tenant),
    user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    
    # Verify project access
    project = tenant_db.query(
        "SELECT * FROM projects WHERE id = ? AND owner_id = ?",
        [project_id, user["id"]]
    )
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get tasks
    tasks = tenant_db.query(
        "SELECT * FROM tasks WHERE project_id = ?",
        [project_id]
    )
    
    return {"tasks": tasks}
```

## Tenant Management

### Admin Dashboard
```python
class TenantAdmin:
    def __init__(self):
        self.db = cinchdb.connect("project_manager")
    
    def get_all_tenants_stats(self):
        """Get statistics for all tenants."""
        if not self.db.is_local:
            raise RuntimeError("Admin functions require local access")
        
        tenants = self.db.tenants.list_tenants()
        stats = []
        
        for tenant in tenants:
            tenant_db = cinchdb.connect(self.db.database, tenant=tenant.name)
            
            # Get counts
            users = tenant_db.query("SELECT COUNT(*) as count FROM users")[0]["count"]
            projects = tenant_db.query("SELECT COUNT(*) as count FROM projects")[0]["count"]
            tasks = tenant_db.query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
            
            # Get activity
            active_users = tenant_db.query("""
                SELECT COUNT(DISTINCT assignee_id) as count 
                FROM tasks 
                WHERE updated_at > datetime('now', '-7 days')
            """)[0]["count"]
            
            stats.append({
                "tenant": tenant.name,
                "users": users,
                "projects": projects,
                "tasks": tasks,
                "active_users_7d": active_users,
                "created_at": tenant.created_at
            })
        
        return stats
    
    def backup_tenant(self, tenant_name: str, backup_path: str):
        """Backup tenant data."""
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)
        
        # Export all tables
        backup_data = {}
        tables = ["users", "projects", "tasks"]
        
        for table in tables:
            data = tenant_db.query(f"SELECT * FROM {table}")
            backup_data[table] = data
        
        # Save to file
        import json
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)
        
        return len(backup_data)
```

## Next Steps

- Deploy with [Remote Access](remote-deployment.md)
- Add [Schema Branching](schema-branching.md) for updates
- Review [Multi-Tenancy Concepts](../concepts/multi-tenancy.md)