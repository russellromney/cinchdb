#!/usr/bin/env python3
"""
Multi-tenant SaaS application example.

This example demonstrates:
- Creating multiple tenants
- Tenant data isolation
- Cross-tenant operations
- Tenant templates
"""

import cinchdb
from cinchdb.models import Column
from datetime import datetime, timedelta
import json


class SaaSApplication:
    def __init__(self, db_name="saas_app"):
        self.db = cinchdb.connect(db_name)
        self.setup_schema()

    def setup_schema(self):
        """Ensure schema exists."""
        try:
            # Create core tables if they don't exist
            self.db.create_table(
                "accounts",
                [
                    Column(name="name", type="TEXT"),
                    Column(name="email", type="TEXT"),
                    Column(name="plan", type="TEXT"),
                    Column(name="status", type="TEXT"),
                ],
            )

            self.db.create_table(
                "projects",
                [
                    Column(name="account_id", type="TEXT"),
                    Column(name="name", type="TEXT"),
                    Column(name="description", type="TEXT", nullable=True),
                    Column(name="status", type="TEXT"),
                ],
            )

            self.db.create_table(
                "tasks",
                [
                    Column(name="project_id", type="TEXT"),
                    Column(name="title", type="TEXT"),
                    Column(name="assignee", type="TEXT", nullable=True),
                    Column(name="status", type="TEXT"),
                    Column(name="due_date", type="TEXT", nullable=True),
                ],
            )

            print("Schema created successfully")
        except:
            print("Schema already exists")

    def onboard_customer(
        self, company_name: str, admin_email: str, plan: str = "trial"
    ):
        """Create a new tenant for a customer."""
        tenant_name = company_name.lower().replace(" ", "_").replace("-", "_")

        print(f"\nOnboarding {company_name}...")

        # Create tenant
        if self.db.is_local:
            self.db.tenants.create_tenant(tenant_name)

        # Create instance for tenant
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)

        # Create account
        account = tenant_db.insert(
            "accounts",
            {
                "name": company_name,
                "email": admin_email,
                "plan": plan,
                "status": "active",
            },
        )

        # Create welcome project
        project = tenant_db.insert(
            "projects",
            {
                "account_id": account["id"],
                "name": "Getting Started",
                "description": "Welcome to our platform! Complete these tasks to get started.",
                "status": "active",
            },
        )

        # Add onboarding tasks
        tasks = [
            ("Complete your profile", "today"),
            ("Invite team members", "tomorrow"),
            ("Create your first project", "this week"),
            ("Explore integrations", "next week"),
        ]

        # Insert all tasks at once using batch insert
        task_records = [
            {
                "project_id": project["id"],
                "title": title,
                "status": "pending",
                "due_date": self._calculate_due_date(due),
            }
            for title, due in tasks
        ]
        tenant_db.insert("tasks", *task_records)

        print(f"✓ Created tenant: {tenant_name}")
        print(f"✓ Created account: {account['id']}")
        print(f"✓ Created welcome project with {len(tasks)} tasks")

        return tenant_name

    def _calculate_due_date(self, due_str: str) -> str:
        """Calculate due date from string."""
        now = datetime.now()

        if due_str == "today":
            due = now
        elif due_str == "tomorrow":
            due = now + timedelta(days=1)
        elif due_str == "this week":
            due = now + timedelta(days=7)
        elif due_str == "next week":
            due = now + timedelta(days=14)
        else:
            due = now

        return due.isoformat()

    def get_tenant_stats(self, tenant_name: str) -> dict:
        """Get statistics for a tenant."""
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)

        # Count entities
        projects = tenant_db.query("SELECT COUNT(*) as count FROM projects")[0]["count"]
        tasks = tenant_db.query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
        completed_tasks = tenant_db.query(
            "SELECT COUNT(*) as count FROM tasks WHERE status = ?", ["completed"]
        )[0]["count"]

        # Get account info
        account = tenant_db.query("SELECT * FROM accounts LIMIT 1")[0]

        return {
            "tenant": tenant_name,
            "company": account["name"],
            "plan": account["plan"],
            "projects": projects,
            "tasks": tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / tasks * 100) if tasks > 0 else 0,
        }

    def get_all_tenants_summary(self) -> list:
        """Get summary of all tenants."""
        if not self.db.is_local:
            print("This operation requires local access")
            return []

        tenants = self.db.tenants.list_tenants()
        summaries = []

        for tenant in tenants:
            if tenant.name.startswith("_") or tenant.name == "main":
                continue  # Skip system tenants

            try:
                stats = self.get_tenant_stats(tenant.name)
                summaries.append(stats)
            except:
                pass  # Skip if tenant has issues

        return summaries

    def simulate_activity(self, tenant_name: str):
        """Simulate some activity for a tenant."""
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)

        print(f"\nSimulating activity for {tenant_name}...")

        # Create a new project
        project = tenant_db.insert(
            "projects",
            {
                "account_id": tenant_db.query("SELECT id FROM accounts LIMIT 1")[0][
                    "id"
                ],
                "name": f"Project {datetime.now().strftime('%Y-%m-%d')}",
                "description": "A new project with important tasks",
                "status": "active",
            },
        )

        # Add tasks
        tasks = [
            "Research phase",
            "Design mockups",
            "Implementation",
            "Testing",
            "Deployment",
        ]

        # Insert all tasks at once using batch insert
        task_records = [
            {
                "project_id": project["id"],
                "title": title,
                "status": "completed" if i < 2 else "pending",
                "due_date": (datetime.now() + timedelta(days=i * 7)).isoformat(),
            }
            for i, title in enumerate(tasks)
        ]
        tenant_db.insert("tasks", *task_records)

        print(f"✓ Created project: {project['name']}")
        print(f"✓ Added {len(tasks)} tasks (2 completed)")


def main():
    print("Multi-Tenant SaaS Example")
    print("=" * 50)

    # Initialize application
    app = SaaSApplication()

    # Onboard customers
    customers = [
        ("Acme Corporation", "admin@acme.com", "professional"),
        ("TechStart Inc", "admin@techstart.com", "startup"),
        ("Enterprise Co", "admin@enterprise.com", "enterprise"),
    ]

    tenant_names = []
    for company, email, plan in customers:
        tenant_name = app.onboard_customer(company, email, plan)
        tenant_names.append(tenant_name)

    # Simulate activity
    for tenant in tenant_names[:2]:  # Activity for first two
        app.simulate_activity(tenant)

    # Show summary
    print("\nTenant Summary")
    print("-" * 50)

    summaries = app.get_all_tenants_summary()
    for summary in summaries:
        print(f"\n{summary['company']} ({summary['tenant']})")
        print(f"  Plan: {summary['plan']}")
        print(f"  Projects: {summary['projects']}")
        print(f"  Tasks: {summary['tasks']} ({summary['completed_tasks']} completed)")
        print(f"  Completion: {summary['completion_rate']:.1f}%")

    # Demonstrate isolation
    print("\nDemonstrating Tenant Isolation")
    print("-" * 50)

    # Query each tenant
    for tenant in tenant_names:
        tenant_db = cinchdb.connect(app.db.database, tenant=tenant)
        account = tenant_db.query("SELECT name FROM accounts LIMIT 1")[0]
        print(f"{tenant}: {account['name']}")

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
