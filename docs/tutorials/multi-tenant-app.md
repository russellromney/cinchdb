# Multi-Tenant SaaS Tutorial

Build a project management SaaS with isolated customer data and shared schema.

## Problem → Solution

**Problem**: Need to isolate customer data while maintaining identical schema across all customers  
**Solution**: CinchDB tenants provide data isolation with automatic schema inheritance

## Quick Setup
```bash
cinch init project_manager
cd project_manager
```

```bash
# Create schema on feature branch
cinch branch create initial-schema
cinch branch switch initial-schema

# Create tables
cinch table create users email:TEXT name:TEXT role:TEXT active:BOOLEAN
cinch table create projects name:TEXT description:TEXT? owner_id:TEXT status:TEXT
cinch table create tasks project_id:TEXT title:TEXT description:TEXT? assignee_id:TEXT? status:TEXT priority:TEXT

# Deploy schema
cinch branch merge-into-main
```

## Customer Onboarding

| Method | Use Case |
|--------|----------|
| CLI | Manual setup, debugging |
| Python SDK | Automated onboarding, APIs |

### CLI Onboarding
```bash
cinch tenant create acme_corp
cinch data insert users --tenant acme_corp --data '{"email": "admin@acme.com", "name": "ACME Admin", "role": "admin", "active": true}'
```

### SDK Onboarding
```python
import cinchdb

def create_customer(company_name: str, admin_email: str):
    db = cinchdb.connect("project_manager")
    
    # Create isolated tenant
    tenant_name = company_name.lower().replace(" ", "_")
    db.create_tenant(tenant_name)
    
    # Connect to tenant
    tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
    
    # Setup admin user and welcome project
    admin = tenant_db.insert("users", {
        "email": admin_email, "name": f"{company_name} Admin", 
        "role": "admin", "active": True
    })
    
    project = tenant_db.insert("projects", {
        "name": "Getting Started", 
        "description": "Welcome to ProjectManager!",
        "owner_id": admin["id"], "status": "active"
    })
    
    # Add sample tasks
    sample_tasks = ["Invite team members", "Create your first project", "Customize settings"]
    for task in sample_tasks:
        tenant_db.insert("tasks", {
            "project_id": project["id"], "title": task,
            "assignee_id": admin["id"], "status": "todo", "priority": "medium"
        })
    
    return {"tenant": tenant_name, "admin_id": admin["id"], "project_id": project["id"]}

# Usage
result = create_customer("ACME Corp", "admin@acme.com")
print(f"Created tenant: {result['tenant']}")
```

## Multi-Tenant API

**Key Pattern**: Validate tenant access before querying tenant-specific data
```python
from fastapi import FastAPI, HTTPException, Depends, Header
import cinchdb

app = FastAPI()

def get_db():
    return cinchdb.connect("project_manager")

def get_current_user(token: str = Header(...)):
    # Validate token and return user info
    return {"id": "user-123", "tenant": "acme_corp"}

@app.get("/projects")
def list_projects(tenant: str = Header(...), user: dict = Depends(get_current_user), db = Depends(get_db)):
    # Security: validate tenant access
    if user["tenant"] != tenant:
        raise HTTPException(403, "Access denied")
    
    # Query tenant-isolated data
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    projects = tenant_db.query("SELECT * FROM projects WHERE owner_id = ?", [user["id"]])
    return {"projects": projects}

@app.post("/projects")
def create_project(project: dict, tenant: str = Header(...), user: dict = Depends(get_current_user), db = Depends(get_db)):
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    new_project = tenant_db.insert("projects", {**project, "owner_id": user["id"], "status": "active"})
    return new_project

@app.get("/tasks/{project_id}")
def list_tasks(project_id: str, tenant: str = Header(...), user: dict = Depends(get_current_user), db = Depends(get_db)):
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    
    # Verify ownership
    project = tenant_db.query("SELECT * FROM projects WHERE id = ? AND owner_id = ?", [project_id, user["id"]])
    if not project:
        raise HTTPException(404, "Project not found")
    
    tasks = tenant_db.query("SELECT * FROM tasks WHERE project_id = ?", [project_id])
    return {"tasks": tasks}
```

## Tenant Management

**Use Case**: Monitor usage, backup data, analyze tenant activity
```python
import cinchdb
import json

def get_tenant_stats():
    """Get statistics for all tenants."""
    db = cinchdb.connect("project_manager")
    # Get statistics for all tenants
    
    tenants = db.list_tenants()
    stats = []
    
    for tenant in tenants:
        tenant_db = cinchdb.connect(db.database, tenant=tenant.name)
        
        # Collect metrics
        users = tenant_db.query("SELECT COUNT(*) as count FROM users")[0]["count"]
        projects = tenant_db.query("SELECT COUNT(*) as count FROM projects")[0]["count"]
        tasks = tenant_db.query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
        
        active_users = tenant_db.query("""
            SELECT COUNT(DISTINCT assignee_id) as count FROM tasks 
            WHERE updated_at > datetime('now', '-7 days')
        """)[0]["count"]
        
        stats.append({
            "tenant": tenant.name, "users": users, "projects": projects, 
            "tasks": tasks, "active_users_7d": active_users, "created_at": tenant.created_at
        })
    
    return stats

def backup_tenant(tenant_name: str, backup_path: str):
    """Export tenant data to JSON."""
    tenant_db = cinchdb.connect("project_manager", tenant=tenant_name)
    
    # Export all tables
    backup_data = {}
    for table in ["users", "projects", "tasks"]:
        backup_data[table] = tenant_db.query(f"SELECT * FROM {table}")
    
    with open(backup_path, "w") as f:
        json.dump(backup_data, f, indent=2)
    
    return len(backup_data)
```

## Next Steps

- Add [Schema Branching](schema-branching.md) for updates
- Review [Multi-Tenancy Concepts](../concepts/multi-tenancy.md)