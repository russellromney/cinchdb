# Security & Encryption

CinchDB provides optional transparent encryption for tenant databases using SQLite3MultipleCiphers.

## Quick Start

```bash
# 1. Generate and save your encryption key
python -c "import secrets; print(secrets.token_urlsafe(32))" > encryption_key.txt
echo "Save this key securely! Store in password manager, env file, or secret management system"

# 2. Add key to environment (replace with your actual key)
export CINCH_ENCRYPTION_KEY="$(cat encryption_key.txt)"

# 3. Enable encryption
export CINCH_ENCRYPT_DATA=true

# 4. Install encryption library
pip install pysqlcipher3

# Or use the encryption extra to install
# pip install cinchdb[encryption]

# For development with uv:
# uv sync --extra encryption

# 5. Clean up temporary file (after storing key securely)
# rm encryption_key.txt
```

## What Gets Encrypted

- ✅ Tenant SQLite databases (`.db`, `.db-wal`, `.db-shm`)
- ✅ All customer business data
- ❌ Metadata database (tenant names, project structure)

This design encrypts sensitive customer data while keeping operational metadata readable for debugging and monitoring.

## Technical Details

- **Cipher**: ChaCha20-Poly1305 with AES fallback
- **Performance**: ~2-5% overhead
- **Integration**: Transparent - no code changes needed
- **Security**: Temporary data encrypted in memory, secure deletion enabled

## Installation

```bash
# Verify encryption support
python -c "
import sqlite3
conn = sqlite3.connect(':memory:')
try:
    conn.execute('PRAGMA key = \"test\"')
    print('✅ Encryption supported')
except:
    print('❌ Install: pip install pysqlcipher3')
conn.close()
"
```

## Key Management

### Best Practices

1. **Generate a secure key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Store securely:**
   - Password managers (1Password, Bitwarden, etc.)
   - Environment files (`.env` with proper `.gitignore`)
   - Cloud secret managers (AWS Secrets Manager, HashiCorp Vault)
   - Never commit keys to version control

3. **Set environment variable:**
   ```bash
   # From secure storage
   export CINCH_ENCRYPTION_KEY="your-actual-key-here"
   
   # From .env file (recommended for development)
   echo "CINCH_ENCRYPTION_KEY=your-actual-key-here" >> .env
   source .env
   ```

### Development vs Production

```bash
# Always provide your own key (required)
export CINCH_ENCRYPTION_KEY="your-secure-key"
export CINCH_ENCRYPT_DATA=true

# No automatic key generation - this prevents data loss
# If no key is provided, CinchDB will fail with a clear error message
```

**Critical**: Store keys securely and separately from database backups. Lost keys cannot recover encrypted data. Back up your keys in multiple secure locations.

## Troubleshooting

### "Failed to apply encryption" error
- Install: `pip install pysqlcipher3`
- Or build SQLite3MultipleCiphers from source

### Performance issues
- Encryption adds ~2-5% overhead
- ChaCha20 cipher is faster than AES
- WAL mode is fully supported