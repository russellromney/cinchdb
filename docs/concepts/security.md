# Security

CinchDB focuses on standard SQLite security features and best practices.

## Database Security

CinchDB uses SQLite's built-in security features:

- **WAL mode**: Provides better concurrency and crash recovery
- **Foreign key constraints**: Enforced for data integrity  
- **Secure deletion**: Overwrites deleted data where possible
- **Memory-based temp storage**: Reduces disk exposure of temporary data

## Access Control

- File system permissions control database access
- Multi-tenant isolation through separate database files
- Branch-based access control for schema changes

## Tenant Encryption

CinchDB supports per-tenant encryption using SQLCipher. You bring the keys, we handle the encryption.

### Usage

```bash
# CLI - Create and query encrypted tenant
cinch tenant create secure --encrypt --key="your-secret-key"
cinch query "SELECT * FROM users" --tenant secure --key="your-secret-key"
```

```python
# Python SDK - Connect to encrypted tenant
db = cinchdb.connect("myapp", tenant="secure", encryption_key="your-secret-key")
users = db.query("SELECT * FROM users")
```

### Key Management

- **You manage keys** - CinchDB never stores encryption keys
- **Provide key for all operations** - Required when accessing encrypted tenants
- **Use environment variables** - Recommended for production

### Requirements

- SQLCipher support (`pip install pysqlcipher3`)
- Consistent key management strategy

## Advanced Security Features

For additional security requirements, consider infrastructure-level solutions such as encrypted file systems, secure networks, and proper access controls.

## Best Practices

1. **File permissions**: Secure your database directories
   ```bash
   chmod 700 /path/to/cinchdb/project
   ```

2. **Backup security**: Secure your database backups appropriately

3. **Network security**: When using API servers, implement proper authentication

4. **Access logs**: Monitor file system access to database files


## Production Considerations

- Use proper file system permissions
- Implement backup encryption at the file system level if needed
- Monitor database access through system logs
- Consider using dedicated database servers with network security