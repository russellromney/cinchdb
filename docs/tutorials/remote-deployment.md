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


## Next Steps

- Review [API Documentation](../api/endpoints.md)
- Set up [Authentication](../api/authentication.md)
- Learn about [Multi-tenancy](../concepts/multi-tenancy.md)