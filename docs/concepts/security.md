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

Encrypt individual tenant databases with your own keys using SQLCipher.

```bash
# CLI
cinch tenant create secure --encrypt --key="your-secret-key"
cinch query "SELECT * FROM users" --tenant secure --key="your-secret-key"
```

```python
# Python SDK
db = cinchdb.connect("myapp", tenant="secure", encryption_key="your-secret-key")
```

**Key points:**
- You manage keys (we don't store them)
- Requires SQLCipher (`pip install pysqlcipher3`)
- Provide key for all operations on encrypted tenants

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