# CinchDB Examples

This directory contains practical examples demonstrating CinchDB features and best practices.

## Python Examples

### [basic_usage.py](python/basic_usage.py)
Getting started with CinchDB Python SDK:
- Connecting to databases
- Creating tables and inserting data
- Querying and updating records
- Working with branches

```bash
python examples/python/basic_usage.py
```

### [multi_tenant.py](python/multi_tenant.py)
Building a multi-tenant SaaS application:
- Creating and managing tenants
- Tenant data isolation
- Cross-tenant operations
- Tenant templates and onboarding

```bash
python examples/python/multi_tenant.py
```

### [branch_workflow.py](python/branch_workflow.py)
Schema branching workflow:
- Creating feature branches
- Making isolated schema changes
- Testing on branches
- Merging changes to main

```bash
python examples/python/branch_workflow.py
```

### [remote_api.py](python/remote_api.py)
Working with remote CinchDB API:
- Connecting to remote servers
- Performing operations over HTTP
- Error handling
- Performance considerations

```bash
# First start the API server
cinch-server serve --create-key

# Then run the example
export CINCHDB_API_KEY=<your-api-key>
python examples/python/remote_api.py
```

## CLI Examples

### [getting_started.sh](cli/getting_started.sh)
Complete CLI walkthrough:
- Project initialization
- Table and column management
- Querying data
- Branch operations
- Multi-tenant setup

```bash
bash examples/cli/getting_started.sh
```

### [branch_workflow.sh](cli/branch_workflow.sh)
Advanced branching scenarios:
- Parallel feature development
- Hotfix workflow
- Branch merging
- Cleanup strategies

```bash
bash examples/cli/branch_workflow.sh
```

### [multi_tenant.sh](cli/multi_tenant.sh)
Multi-tenant SaaS platform setup:
- Tenant creation and management
- Tenant-specific data
- Schema synchronization
- Tenant isolation demonstration

```bash
bash examples/cli/multi_tenant.sh
```

## Running the Examples

1. **Install CinchDB**:
   ```bash
   pip install cinchdb
   ```

2. **Python Examples**:
   ```bash
   cd examples/python
   python basic_usage.py
   ```

3. **CLI Examples**:
   ```bash
   cd examples/cli
   bash getting_started.sh
   ```

## Key Concepts Demonstrated

### Schema Management
- Creating tables with automatic ID and timestamp fields
- Adding and modifying columns
- Creating views for complex queries
- Managing indexes

### Branching
- Isolating schema changes in branches
- Parallel development workflows
- Safe testing before merging
- Merge strategies

### Multi-Tenancy
- Complete data isolation per tenant
- Shared schema across tenants
- Tenant lifecycle management
- Scaling considerations

### Remote Access
- API-based database access
- Authentication with API keys
- Performance optimization
- Error handling

## Best Practices

1. **Always use branches** for schema changes
2. **Test thoroughly** before merging to main
3. **Use parameterized queries** to prevent SQL injection
4. **Implement proper error handling** for production code
5. **Monitor performance** when scaling tenants
6. **Secure API keys** using environment variables

## Next Steps

- Read the [full documentation](https://cinchdb.com/docs)
- Explore the [Python SDK API Reference](https://cinchdb.com/docs/python-sdk/api-reference)
- Learn about [deployment options](https://cinchdb.com/docs/tutorials/remote-deployment)
- Join the [community discussions](https://github.com/russellromney/cinchdb/discussions)