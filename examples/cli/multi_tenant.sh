#!/bin/bash
# CinchDB Multi-Tenant Example

echo "CinchDB Multi-Tenant Example"
echo "============================"
echo

# Initialize project
echo "Setting up multi-tenant SaaS project..."
cinch init saas_platform
cd saas_platform

# Create schema for SaaS application
echo -e "\n1. Creating SaaS application schema..."
cinch table create organizations \
  name:TEXT \
  plan:TEXT \
  status:TEXT \
  max_users:INTEGER

cinch table create users \
  org_id:TEXT \
  email:TEXT \
  name:TEXT \
  role:TEXT \
  is_active:BOOLEAN

cinch table create projects \
  org_id:TEXT \
  name:TEXT \
  description:TEXT? \
  status:TEXT \
  budget:REAL?

cinch table create tasks \
  project_id:TEXT \
  title:TEXT \
  description:TEXT? \
  assignee_id:TEXT? \
  status:TEXT \
  priority:TEXT \
  due_date:TEXT?

echo "Schema created successfully"

# Create tenants for different customers
echo -e "\n2. Creating tenants for customers..."
cinch tenant create acme_corp
cinch tenant create startup_inc
cinch tenant create enterprise_co

echo -e "\nTenants created:"
cinch tenant list

# Add data to each tenant
echo -e "\n3. Setting up Acme Corp (tenant: acme_corp)..."
# Acme Corp data
cinch query "INSERT INTO organizations (name, plan, status, max_users) VALUES ('Acme Corporation', 'professional', 'active', 50)" --tenant acme_corp

cinch query "INSERT INTO users (org_id, email, name, role, is_active) VALUES \
  ('org_123', 'admin@acme.com', 'Acme Admin', 'admin', true), \
  ('org_123', 'john@acme.com', 'John Doe', 'member', true), \
  ('org_123', 'jane@acme.com', 'Jane Smith', 'member', true)" --tenant acme_corp

cinch query "INSERT INTO projects (org_id, name, description, status, budget) VALUES \
  ('org_123', 'Website Redesign', 'Complete redesign of corporate website', 'active', 50000), \
  ('org_123', 'Mobile App', 'Native mobile application', 'planning', 100000)" --tenant acme_corp

echo -e "\n4. Setting up Startup Inc (tenant: startup_inc)..."
# Startup Inc data
cinch query "INSERT INTO organizations (name, plan, status, max_users) VALUES ('Startup Inc', 'startup', 'active', 10)" --tenant startup_inc

cinch query "INSERT INTO users (org_id, email, name, role, is_active) VALUES \
  ('org_456', 'founder@startup.com', 'Startup Founder', 'admin', true), \
  ('org_456', 'dev@startup.com', 'Lead Developer', 'member', true)" --tenant startup_inc

cinch query "INSERT INTO projects (org_id, name, description, status, budget) VALUES \
  ('org_456', 'MVP Development', 'Minimum viable product', 'active', 10000)" --tenant startup_inc

echo -e "\n5. Setting up Enterprise Co (tenant: enterprise_co)..."
# Enterprise Co data
cinch query "INSERT INTO organizations (name, plan, status, max_users) VALUES ('Enterprise Co', 'enterprise', 'active', 500)" --tenant enterprise_co

cinch query "INSERT INTO users (org_id, email, name, role, is_active) VALUES \
  ('org_789', 'cto@enterprise.com', 'Enterprise CTO', 'admin', true), \
  ('org_789', 'pm@enterprise.com', 'Project Manager', 'member', true), \
  ('org_789', 'qa@enterprise.com', 'QA Lead', 'member', true)" --tenant enterprise_co

# Show tenant isolation
echo -e "\n6. Demonstrating tenant isolation..."
echo -e "\nUsers in Acme Corp:"
cinch query "SELECT name, email, role FROM users" --tenant acme_corp

echo -e "\nUsers in Startup Inc:"
cinch query "SELECT name, email, role FROM users" --tenant startup_inc

echo -e "\nUsers in Enterprise Co:"
cinch query "SELECT name, email, role FROM users" --tenant enterprise_co

# Aggregate queries per tenant
echo -e "\n7. Tenant statistics..."
echo -e "\nAcme Corp stats:"
cinch query "SELECT \
  (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users, \
  (SELECT COUNT(*) FROM projects) as total_projects, \
  (SELECT SUM(budget) FROM projects) as total_budget" --tenant acme_corp

echo -e "\nStartup Inc stats:"
cinch query "SELECT \
  (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users, \
  (SELECT COUNT(*) FROM projects) as total_projects, \
  (SELECT SUM(budget) FROM projects) as total_budget" --tenant startup_inc

# Create tenant-specific view
echo -e "\n8. Creating tenant-specific views..."
cinch view create active_projects \
  "SELECT p.*, u.name as assignee_name \
   FROM projects p \
   LEFT JOIN tasks t ON p.id = t.project_id \
   LEFT JOIN users u ON t.assignee_id = u.id \
   WHERE p.status = 'active' \
   GROUP BY p.id" --tenant acme_corp

echo -e "\nActive projects for Acme Corp:"
cinch query "SELECT name, description, budget FROM active_projects" --tenant acme_corp

# Schema changes apply to all tenants
echo -e "\n9. Making schema changes (applies to all tenants)..."
cinch column add organizations subscription_ends:TEXT?
cinch column add users last_login:TEXT?

echo -e "\nVerifying schema change in all tenants:"
echo "Acme Corp organizations table:"
cinch table info organizations --tenant acme_corp | grep subscription_ends

echo "Startup Inc organizations table:"
cinch table info organizations --tenant startup_inc | grep subscription_ends

# Copy tenant for testing
echo -e "\n10. Creating test tenant from template..."
cinch tenant copy acme_corp test_environment

echo -e "\nData in test environment:"
cinch query "SELECT COUNT(*) as user_count FROM users" --tenant test_environment

# Clean up test tenant
echo -e "\n11. Cleaning up test tenant..."
cinch tenant delete test_environment --force

echo -e "\nRemaining tenants:"
cinch tenant list

# Summary
echo -e "\n12. Multi-tenant summary..."
echo -e "\nEach tenant has:"
echo "  - Completely isolated data"
echo "  - Same schema structure"
echo "  - Independent SQLite database file"
echo "  - Can be queried separately"

echo -e "\nDatabase files created:"
ls -la .cinchdb/databases/main/branches/main/tenants/

echo -e "\nMulti-tenant example completed!"
echo -e "\nKey concepts demonstrated:"
echo "  - Tenant creation and management"
echo "  - Complete data isolation"
echo "  - Schema synchronization across tenants"
echo "  - Tenant-specific operations"
echo "  - Tenant copying for testing"