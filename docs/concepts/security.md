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

## Advanced Security Features

For advanced security requirements, consider infrastructure-level solutions such as encrypted file systems, secure networks, and proper access controls.

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