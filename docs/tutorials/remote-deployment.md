# Remote Deployment Guide

Deploy CinchDB as a remote API server for production use.

## Overview

CinchDB can run as a FastAPI server providing:
- REST API access to all operations
- Multi-user support with API keys
- Remote database management
- Scalable architecture

## Quick Start

### 1. Install with Server Dependencies
```bash
pip install cinchdb[server]
```

### 2. Start Server
```bash
# Create initial API key
cinch-server serve --create-key

# Output:
# Created API key: ck_live_a1b2c3d4e5f6...
# Server running at http://localhost:8000
```

### 3. Configure Client
```bash
# Add remote configuration
cinch remote add production \
  --url http://localhost:8000 \
  --key ck_live_a1b2c3d4e5f6...

# Use remote
cinch remote use production
```

## Production Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Run server
CMD ["cinch-server", "serve", "--host", "0.0.0.0", "--port", "8000", "--data-dir", "/data"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  cinchdb:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - cinchdb-data:/data
    environment:
      - CINCHDB_DATA_DIR=/data
      - CINCHDB_LOG_LEVEL=info
    restart: unless-stopped

volumes:
  cinchdb-data:
```

Deploy:
```bash
docker-compose up -d
```

### Kubernetes Deployment

Create `deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cinchdb
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cinchdb
  template:
    metadata:
      labels:
        app: cinchdb
    spec:
      containers:
      - name: cinchdb
        image: cinchdb:latest
        ports:
        - containerPort: 8000
        env:
        - name: CINCHDB_DATA_DIR
          value: /data
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: cinchdb-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: cinchdb-service
spec:
  selector:
    app: cinchdb
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cinchdb-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Configuration

### Environment Variables
```bash
# Data directory
export CINCHDB_DATA_DIR=/var/lib/cinchdb

# API settings
export CINCHDB_API_PREFIX=/api/v1
export CINCHDB_CORS_ORIGINS=https://app.example.com

# Performance
export CINCHDB_WORKERS=4
export CINCHDB_MAX_CONNECTIONS=100

# Security
export CINCHDB_API_KEY_HEADER=X-API-Key
export CINCHDB_ENABLE_DOCS=false  # Disable in production
```

### Configuration File

Create `cinchdb.conf`:
```toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4
log_level = "info"

[database]
data_dir = "/var/lib/cinchdb"
max_connections = 100
connection_timeout = 30

[security]
enable_docs = false
cors_origins = ["https://app.example.com"]
api_key_header = "X-API-Key"

[monitoring]
enable_metrics = true
metrics_port = 9090
```

## API Key Management

### Create API Keys
```python
import cinchdb.api.auth as auth

# Create read-write key
rw_key = auth.create_api_key(
    name="production-app",
    permissions=["read", "write"],
    databases=["myapp"]
)

# Create read-only key
ro_key = auth.create_api_key(
    name="analytics-service",
    permissions=["read"],
    databases=["myapp"],
    branches=["main"]  # Restrict to main branch
)

# Create tenant-specific key
tenant_key = auth.create_api_key(
    name="customer-api",
    permissions=["read", "write"],
    databases=["myapp"],
    tenants=["customer_123"]  # Restrict to single tenant
)
```

### Key Rotation
```python
def rotate_api_keys():
    """Rotate API keys periodically."""
    old_keys = auth.list_api_keys()
    new_keys = []
    
    for old_key in old_keys:
        # Create new key with same permissions
        new_key = auth.create_api_key(
            name=f"{old_key.name}-rotated",
            permissions=old_key.permissions,
            databases=old_key.databases
        )
        new_keys.append(new_key)
        
        # Schedule old key deletion
        auth.schedule_key_deletion(old_key.id, days=7)
    
    return new_keys
```

## Load Balancing

### Nginx Configuration
```nginx
upstream cinchdb {
    least_conn;
    server cinchdb1:8000;
    server cinchdb2:8000;
    server cinchdb3:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location / {
        proxy_pass http://cinchdb;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://cinchdb/health;
        access_log off;
    }
}
```

## Monitoring

### Health Checks
```python
import requests

def check_health(api_url: str) -> dict:
    """Check CinchDB server health."""
    response = requests.get(f"{api_url}/health")
    return response.json()

# Monitor in production
health = check_health("https://api.example.com")
print(f"Status: {health['status']}")
print(f"Version: {health['version']}")
print(f"Uptime: {health['uptime']}")
```

### Prometheus Metrics

Enable metrics endpoint:
```bash
cinch-server serve --enable-metrics
```

Prometheus configuration:
```yaml
scrape_configs:
  - job_name: 'cinchdb'
    static_configs:
      - targets: ['cinchdb:9090']
    metrics_path: '/metrics'
```

### Logging

Configure structured logging:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'tenant'):
            log_data['tenant'] = record.tenant
            
        return json.dumps(log_data)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger('cinchdb')
logger.addHandler(handler)
```

## Security

### TLS/SSL

Always use HTTPS in production:
```python
# Generate self-signed cert for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run with SSL
cinch-server serve --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Rate Limiting

Implement rate limiting:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/query")
@limiter.limit("100/minute")
async def query_endpoint():
    # Handle query
    pass
```

### API Key Security

Best practices:
1. Use strong, random keys
2. Rotate keys regularly
3. Set expiration dates
4. Limit scope (database/branch/tenant)
5. Monitor usage

## Backup and Recovery

### Automated Backups
```python
import schedule
import time
import shutil
from datetime import datetime

def backup_databases():
    """Backup all CinchDB databases."""
    data_dir = "/var/lib/cinchdb"
    backup_dir = f"/backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create backup
    shutil.copytree(data_dir, backup_dir)
    
    # Compress
    shutil.make_archive(backup_dir, 'gztar', backup_dir)
    
    # Upload to cloud storage
    upload_to_s3(f"{backup_dir}.tar.gz")
    
    # Clean up old backups
    cleanup_old_backups()

# Schedule daily backups
schedule.every().day.at("02:00").do(backup_databases)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Disaster Recovery

Create recovery plan:
```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
RESTORE_DIR=/var/lib/cinchdb

# Stop service
systemctl stop cinchdb

# Backup current data
mv $RESTORE_DIR $RESTORE_DIR.old

# Extract backup
tar -xzf $BACKUP_FILE -C /

# Verify integrity
cinchdb-verify $RESTORE_DIR

# Start service
systemctl start cinchdb
```

## Performance Tuning

### Connection Pooling
```python
# Configure in server startup
app.state.connection_pool = ConnectionPool(
    min_connections=10,
    max_connections=100,
    connection_timeout=30
)
```

### Caching
```python
from functools import lru_cache
import redis

# Redis cache for frequently accessed data
cache = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1000)
def get_tenant_metadata(tenant_id: str) -> dict:
    """Cache tenant metadata."""
    # Check Redis first
    cached = cache.get(f"tenant:{tenant_id}")
    if cached:
        return json.loads(cached)
    
    # Load from database
    metadata = load_tenant_metadata(tenant_id)
    
    # Cache for 1 hour
    cache.setex(f"tenant:{tenant_id}", 3600, json.dumps(metadata))
    
    return metadata
```

### Query Optimization
```python
# Add indexes for common queries
def optimize_tenant_queries(db, tenant):
    tenant_db = db.switch_tenant(tenant)
    
    # Add indexes
    tenant_db.query("CREATE INDEX idx_users_email ON users(email)")
    tenant_db.query("CREATE INDEX idx_users_active ON users(active)")
    tenant_db.query("CREATE INDEX idx_orders_user_id ON orders(user_id)")
    tenant_db.query("CREATE INDEX idx_orders_status ON orders(status)")
```

## Scaling Strategies

### Horizontal Scaling
- Deploy multiple API servers
- Use load balancer
- Share data directory (NFS/EFS)
- Or implement sharding

### Sharding by Tenant
```python
def get_shard_for_tenant(tenant_id: str) -> str:
    """Determine which shard holds a tenant."""
    # Simple hash-based sharding
    shard_count = 4
    hash_value = hash(tenant_id)
    shard_num = hash_value % shard_count
    return f"shard_{shard_num}"

# Route to appropriate server
SHARD_SERVERS = {
    "shard_0": "http://shard0.internal:8000",
    "shard_1": "http://shard1.internal:8000",
    "shard_2": "http://shard2.internal:8000",
    "shard_3": "http://shard3.internal:8000",
}

def route_request(tenant_id: str, request):
    shard = get_shard_for_tenant(tenant_id)
    server = SHARD_SERVERS[shard]
    # Forward request to appropriate shard
```

## Client Configuration

### Python Client
```python
# Production client setup
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key=os.environ["CINCHDB_API_KEY"],
    database="production",
    # Connection pooling
    max_connections=50,
    connection_timeout=30,
    # Retry logic
    max_retries=3,
    retry_delay=1.0
)
```

### CLI Configuration
```bash
# Configure for production
cinch remote add prod \
  --url https://api.example.com \
  --key $CINCHDB_PROD_KEY

# Set as default
cinch remote use prod
```

## Next Steps

- Review [API Documentation](../api/endpoints.md)
- Set up [Authentication](../api/authentication.md)
- Learn about [Multi-tenancy](../concepts/multi-tenancy.md)