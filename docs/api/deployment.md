# API Server Deployment

Deploy CinchDB API server for production use.

## Quick Start

### Local Development
```bash
# Install with server dependencies
pip install cinchdb[server]

# Start server with auto-generated API key
cinch-server serve --create-key

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Basic Production Setup
```bash
# Set environment variables
export CINCHDB_DATA_DIR=/var/lib/cinchdb
export CINCHDB_LOG_LEVEL=info

# Start with production settings
cinch-server serve \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --no-docs
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir cinchdb[server]

# Create data directory
RUN mkdir -p /data

# Copy configuration (if any)
COPY cinchdb.conf /app/

EXPOSE 8000

# Run server
CMD ["cinch-server", "serve", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--data-dir", "/data"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  cinchdb:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - cinchdb-data:/data
      - ./cinchdb.conf:/app/cinchdb.conf
    environment:
      - CINCHDB_DATA_DIR=/data
      - CINCHDB_LOG_LEVEL=info
      - CINCHDB_WORKERS=4
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  cinchdb-data:
```

## Cloud Platform Deployment

### AWS ECS

Task definition:
```json
{
  "family": "cinchdb",
  "taskRoleArn": "arn:aws:iam::123456789012:role/cinchdb-task-role",
  "executionRoleArn": "arn:aws:iam::123456789012:role/cinchdb-execution-role",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "cinchdb",
      "image": "your-registry/cinchdb:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "CINCHDB_DATA_DIR", "value": "/data"},
        {"name": "CINCHDB_WORKERS", "value": "4"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "cinchdb-data",
          "containerPath": "/data"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cinchdb",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "cinchdb-data",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-12345678"
      }
    }
  ],
  "cpu": "1024",
  "memory": "2048"
}
```

### Google Cloud Run

Deploy with persistent disk:
```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/cinchdb

# Deploy to Cloud Run
gcloud run deploy cinchdb \
  --image gcr.io/PROJECT_ID/cinchdb \
  --platform managed \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "CINCHDB_DATA_DIR=/data,CINCHDB_WORKERS=4" \
  --execution-environment gen2 \
  --service-account cinchdb-sa@PROJECT_ID.iam.gserviceaccount.com
```

### Kubernetes

Deployment manifest:
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
        - name: CINCHDB_WORKERS
          value: "4"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
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
```

## Production Configuration

### Environment Variables

```bash
# Core settings
CINCHDB_DATA_DIR=/var/lib/cinchdb      # Data directory path
CINCHDB_LOG_LEVEL=info                  # Log level (debug, info, warning, error)
CINCHDB_WORKERS=4                       # Number of worker processes

# API settings  
CINCHDB_API_PREFIX=/api/v1              # API URL prefix
CINCHDB_ENABLE_DOCS=false               # Disable Swagger docs in production
CINCHDB_CORS_ORIGINS=https://app.com    # Allowed CORS origins

# Performance
CINCHDB_MAX_CONNECTIONS=100             # Max database connections
CINCHDB_CONNECTION_TIMEOUT=30           # Connection timeout in seconds
CINCHDB_REQUEST_TIMEOUT=300             # Request timeout in seconds

# Security
CINCHDB_API_KEY_HEADER=X-API-Key        # Header name for API key
CINCHDB_ENABLE_METRICS=true             # Enable Prometheus metrics
CINCHDB_METRICS_PORT=9090               # Metrics endpoint port
```

### Configuration File

`cinchdb.conf`:
```toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4
log_level = "info"
enable_docs = false

[database]
data_dir = "/var/lib/cinchdb"
max_connections = 100
connection_timeout = 30
checkpoint_interval = 300

[api]
prefix = "/api/v1"
max_request_size = 10485760  # 10MB
request_timeout = 300

[security]
api_key_header = "X-API-Key"
cors_origins = ["https://app.example.com"]
cors_methods = ["GET", "POST", "PUT", "DELETE"]
cors_headers = ["Content-Type", "X-API-Key"]

[monitoring]
enable_metrics = true
metrics_port = 9090
enable_tracing = false
```

## Reverse Proxy Setup

### Nginx

```nginx
upstream cinchdb_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/api.example.com.crt;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
    limit_req zone=api burst=200 nodelay;

    location / {
        proxy_pass http://cinchdb_backend;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # Large requests (file uploads)
        client_max_body_size 10m;
    }

    location /health {
        proxy_pass http://cinchdb_backend/health;
        access_log off;
    }

    location /metrics {
        proxy_pass http://127.0.0.1:9090/metrics;
        allow 10.0.0.0/8;  # Internal network only
        deny all;
    }
}
```

### Apache

```apache
<VirtualHost *:443>
    ServerName api.example.com
    
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/api.example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/api.example.com.key
    
    # Proxy settings
    ProxyPreserveHost On
    ProxyPass / http://localhost:8000/
    ProxyPassReverse / http://localhost:8000/
    
    # Headers
    RequestHeader set X-Forwarded-Proto "https"
    Header always set Strict-Transport-Security "max-age=31536000"
    
    # Timeouts
    ProxyTimeout 300
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/cinchdb_error.log
    CustomLog ${APACHE_LOG_DIR}/cinchdb_access.log combined
</VirtualHost>
```

## Systemd Service

`/etc/systemd/system/cinchdb.service`:
```ini
[Unit]
Description=CinchDB API Server
After=network.target

[Service]
Type=exec
User=cinchdb
Group=cinchdb
WorkingDirectory=/opt/cinchdb
Environment="CINCHDB_DATA_DIR=/var/lib/cinchdb"
Environment="CINCHDB_LOG_LEVEL=info"
ExecStart=/usr/local/bin/cinch-server serve --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/cinchdb

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/health
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

### Prometheus Metrics

Enable metrics endpoint:
```bash
cinch-server serve --enable-metrics
```

Key metrics:
- `cinchdb_requests_total` - Total API requests
- `cinchdb_request_duration_seconds` - Request latency
- `cinchdb_active_connections` - Active DB connections
- `cinchdb_query_duration_seconds` - Query execution time

### Logging

Configure structured logging:
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": getattr(record, 'request_id', None)
        })

# Apply formatter
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

## Security Hardening

### API Key Management
- Rotate keys regularly
- Use strong random keys
- Implement key expiration
- Log key usage

### Network Security
- Use HTTPS only
- Implement rate limiting
- Whitelist IP addresses
- Use Web Application Firewall

### Database Security
- Encrypt data at rest
- Regular backups
- Access logging
- File permissions (600)

## Performance Tuning

### Connection Pooling
```python
# Configure in server startup
POOL_SIZE = int(os.environ.get("CINCHDB_POOL_SIZE", 50))
MAX_OVERFLOW = int(os.environ.get("CINCHDB_MAX_OVERFLOW", 100))
```

### Query Optimization
- Add indexes on frequently queried columns
- Use connection pooling
- Implement query caching
- Monitor slow queries

### Resource Limits
```bash
# File descriptors
ulimit -n 65536

# Processes
ulimit -u 4096

# Memory (in KB)
ulimit -m 8388608
```

## Backup and Recovery

### Automated Backups
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/cinchdb"
DATA_DIR="/var/lib/cinchdb"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/cinchdb_$DATE.tar.gz" -C "$DATA_DIR" .

# Upload to S3
aws s3 cp "$BACKUP_DIR/cinchdb_$DATE.tar.gz" s3://my-backups/cinchdb/

# Keep only last 30 days
find "$BACKUP_DIR" -name "cinchdb_*.tar.gz" -mtime +30 -delete
```

### Restore Process
```bash
# Stop service
systemctl stop cinchdb

# Backup current data
mv /var/lib/cinchdb /var/lib/cinchdb.old

# Extract backup
tar -xzf /backups/cinchdb_20240115_020000.tar.gz -C /var/lib/cinchdb

# Set permissions
chown -R cinchdb:cinchdb /var/lib/cinchdb

# Start service
systemctl start cinchdb
```

## Next Steps

- [Authentication Setup](authentication.md)
- [API Endpoints Reference](endpoints.md)
- [API Reference](endpoints.md)