# API Endpoints Reference

Complete reference for all CinchDB API endpoints.

## Base URL

```
https://api.your-domain.com/api/v1
```

## Authentication

All requests require API key authentication:

```bash
curl -H "X-API-Key: ck_live_your_key_here" \
     https://api.example.com/api/v1/tables
```

## Database Operations

### List Databases

```http
GET /databases
```

Response:
```json
{
  "databases": [
    {
      "name": "myapp",
      "created_at": "2024-01-15T10:30:00Z",
      "size_mb": 12.5,
      "branch_count": 3,
      "tenant_count": 5
    }
  ]
}
```

### Create Database

```http
POST /databases
```

Request:
```json
{
  "name": "new_database"
}
```

## Table Operations

### List Tables

```http
GET /tables?database=myapp&branch=main&tenant=main
```

Response:
```json
{
  "tables": [
    {
      "name": "users",
      "row_count": 1000,
      "size_kb": 128,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Create Table

```http
POST /tables
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "table_name": "products",
  "columns": [
    {
      "name": "name",
      "type": "TEXT",
      "nullable": false
    },
    {
      "name": "price",
      "type": "REAL",
      "nullable": false
    },
    {
      "name": "description",
      "type": "TEXT",
      "nullable": true
    }
  ]
}
```

### Get Table Info

```http
GET /tables/{table_name}?database=myapp&branch=main&tenant=main
```

Response:
```json
{
  "table": "products",
  "columns": [
    {
      "name": "id",
      "type": "TEXT",
      "primary_key": true,
      "nullable": false
    },
    {
      "name": "name",
      "type": "TEXT",
      "nullable": false
    }
  ],
  "indexes": [],
  "row_count": 50
}
```

### Drop Table

```http
DELETE /tables/{table_name}?database=myapp&branch=main&tenant=main
```

## Column Operations

### Add Column

```http
POST /tables/{table_name}/columns
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "column": {
    "name": "category",
    "type": "TEXT",
    "nullable": true,
    "default": null
  }
}
```

### Drop Column

```http
DELETE /tables/{table_name}/columns/{column_name}?database=myapp&branch=main&tenant=main
```

### Alter Column Nullable

```http
PUT /columns/{table_name}/{column_name}/nullable
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "nullable": false,
  "fill_value": "default_value"
}
```

Response:
```json
{
  "message": "Made column 'phone' NOT NULL in table 'users'"
}
```

## Data Operations

### Query

```http
POST /query
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "sql": "SELECT * FROM users WHERE active = ?",
  "params": [true]
}
```

Response:
```json
{
  "results": [
    {
      "id": "user_123",
      "email": "alice@example.com",
      "active": true
    }
  ],
  "row_count": 1,
  "execution_time_ms": 2.5
}
```

### Insert

```http
POST /tables/{table_name}/rows
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "data": {
    "name": "New Product",
    "price": 29.99,
    "category": "Electronics"
  }
}
```

Response:
```json
{
  "id": "prod_456",
  "name": "New Product",
  "price": 29.99,
  "category": "Electronics",
  "created_at": "2024-01-15T14:30:00Z",
  "updated_at": "2024-01-15T14:30:00Z"
}
```

### Update

```http
PUT /tables/{table_name}/rows/{id}
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "data": {
    "price": 24.99,
    "updated_at": "2024-01-15T15:00:00Z"
  }
}
```

### Delete

```http
DELETE /tables/{table_name}/rows/{id}?database=myapp&branch=main&tenant=main
```

### Bulk Insert

```http
POST /tables/{table_name}/bulk
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "data": [
    {"name": "Product 1", "price": 10.00},
    {"name": "Product 2", "price": 20.00},
    {"name": "Product 3", "price": 30.00}
  ]
}
```

Response:
```json
{
  "inserted": 3,
  "ids": ["prod_1", "prod_2", "prod_3"]
}
```

## Branch Operations

### List Branches

```http
GET /branches?database=myapp
```

Response:
```json
{
  "branches": [
    {
      "name": "main",
      "created_at": "2024-01-01T00:00:00Z",
      "parent": null,
      "is_default": true
    },
    {
      "name": "feature.new-ui",
      "created_at": "2024-01-10T00:00:00Z",
      "parent": "main",
      "is_default": false
    }
  ]
}
```

### Create Branch

```http
POST /branches
```

Request:
```json
{
  "database": "myapp",
  "name": "feature.payments",
  "from_branch": "main"
}
```

### Switch Branch

```http
PUT /branches/current
```

Request:
```json
{
  "database": "myapp",
  "branch": "feature.payments"
}
```

### Merge Branch

```http
POST /branches/merge
```

Request:
```json
{
  "database": "myapp",
  "source": "feature.payments",
  "target": "main"
}
```

### Delete Branch

```http
DELETE /branches/{branch_name}?database=myapp
```

## Tenant Operations

### List Tenants

```http
GET /tenants?database=myapp
```

Response:
```json
{
  "tenants": [
    {
      "name": "main",
      "created_at": "2024-01-01T00:00:00Z",
      "is_default": true
    },
    {
      "name": "customer_123",
      "created_at": "2024-01-05T00:00:00Z",
      "is_default": false
    }
  ]
}
```

### Create Tenant

```http
POST /tenants
```

Request:
```json
{
  "database": "myapp",
  "name": "customer_456",
  "copy_from": "main"
}
```

### Delete Tenant

```http
DELETE /tenants/{tenant_name}?database=myapp
```

## View Operations

### List Views

```http
GET /views?database=myapp&branch=main&tenant=main
```

### Create View

```http
POST /views
```

Request:
```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "main",
  "name": "active_users",
  "query": "SELECT * FROM users WHERE active = true"
}
```

### Drop View

```http
DELETE /views/{view_name}?database=myapp&branch=main&tenant=main
```

## System Operations

### Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "database": {
    "connected": true,
    "databases": 5,
    "total_size_mb": 1024
  }
}
```

### Server Info

```http
GET /info
```

Response:
```json
{
  "version": "1.0.0",
  "features": {
    "branching": true,
    "multi_tenant": true,
    "remote_api": true
  },
  "limits": {
    "max_databases": 100,
    "max_branches_per_db": 50,
    "max_tenants_per_db": 1000,
    "max_request_size_mb": 10
  }
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics.

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request

```json
{
  "error": "Bad Request",
  "message": "Invalid SQL syntax",
  "details": {
    "line": 1,
    "column": 15
  }
}
```

### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```

### 403 Forbidden

```json
{
  "error": "Forbidden",
  "message": "Insufficient permissions for operation"
}
```

### 404 Not Found

```json
{
  "error": "Not Found",
  "message": "Table 'users' not found"
}
```

### 429 Too Many Requests

```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "retry_after": 60
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "request_id": "req_123456"
}
```

## Rate Limiting

Default rate limits:
- 1000 requests per hour per API key
- 100 concurrent connections
- 10MB max request size

Custom limits can be configured per API key.

## Pagination

For endpoints returning lists, use pagination parameters:

```http
GET /tables/{table_name}/rows?limit=100&offset=200
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "offset": 200,
    "limit": 100,
    "total": 5000,
    "has_more": true
  }
}
```

## Filtering and Sorting

### Filtering

```http
GET /tables/{table_name}/rows?filter={"active":true,"role":"admin"}
```

### Sorting

```http
GET /tables/{table_name}/rows?sort=created_at:desc,name:asc
```

## Batch Operations

### Batch Query

```http
POST /batch
```

Request:
```json
{
  "database": "myapp",
  "operations": [
    {
      "type": "query",
      "sql": "SELECT COUNT(*) FROM users"
    },
    {
      "type": "insert",
      "table": "logs",
      "data": {"message": "Batch operation"}
    }
  ]
}
```

Response:
```json
{
  "results": [
    {"success": true, "data": [{"count": 1000}]},
    {"success": true, "data": {"id": "log_123"}}
  ]
}
```

## WebSocket API

For real-time updates:

```javascript
const ws = new WebSocket('wss://api.example.com/ws');

ws.send(JSON.stringify({
  type: 'subscribe',
  database: 'myapp',
  table: 'orders',
  events: ['insert', 'update']
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Change:', data);
};
```

## SDK Usage

### Python

```python
from cinchdb import CinchDB

db = CinchDB(
    "myapp",
    remote_url="https://api.example.com",
    api_key="ck_live_your_key"
)

users = db.query("SELECT * FROM users")
```

### JavaScript/TypeScript

```javascript
import { CinchDB } from '@cinchdb/client';

const db = new CinchDB({
  database: 'myapp',
  apiUrl: 'https://api.example.com',
  apiKey: 'ck_live_your_key'
});

const users = await db.query('SELECT * FROM users');
```

## Next Steps

- [Authentication Guide](authentication.md)
- [Authentication Guide](authentication.md)
- [Deployment Guide](deployment.md)