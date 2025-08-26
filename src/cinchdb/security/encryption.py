"""Simple SQLite encryption using environment variables with KMS upgrade path."""

import os
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteEncryption:
    """Simple SQLite encryption with static keys and KMS upgrade path."""
    
    def __init__(self):
        # Encryption is optional for open source users
        self.enabled = os.getenv("CINCH_ENCRYPT_DATA", "false").lower() == "true"
        self._encryption_key = None
        
        if self.enabled:
            self._encryption_key = self._get_encryption_key()
    
    def _get_encryption_key(self) -> str:
        """Get encryption key with future KMS support."""
        
        # Future KMS support - check for KMS configuration first
        kms_provider = os.getenv("CINCH_KMS_PROVIDER")
        if kms_provider:
            # TODO: Implement KMS key retrieval
            # return self._get_key_from_kms(kms_provider)
            logger.warning("KMS provider configured but not implemented yet")
        
        # Require explicit key
        static_key = os.getenv("CINCH_ENCRYPTION_KEY")
        if static_key:
            return static_key
        
        # Fail fast if no key provided
        raise ValueError(
            "CINCH_ENCRYPTION_KEY environment variable is required when CINCH_ENCRYPT_DATA=true. "
            "Generate a key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    
    def get_connection(self, db_path: Path) -> sqlite3.Connection:
        """Get SQLite connection with optional encryption."""
        # Connect with datetime parsing support
        conn = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        
        if self.enabled and self._encryption_key:
            try:
                # Apply encryption key
                conn.execute(f"PRAGMA key = '{self._encryption_key}'")
                
                # Configure recommended cipher (ChaCha20-Poly1305) if supported
                try:
                    conn.execute("PRAGMA cipher = 'chacha20'")
                except sqlite3.OperationalError:
                    # Fallback to default cipher if ChaCha20 not available
                    logger.debug("ChaCha20 cipher not available, using default")
                
                # Security hardening
                conn.execute("PRAGMA temp_store = MEMORY")  # Encrypt temp data
                conn.execute("PRAGMA secure_delete = ON")   # Overwrite deleted data
                
            except sqlite3.OperationalError as e:
                logger.error(f"Failed to apply encryption to {db_path}: {e}")
                # Close connection and re-raise with helpful message
                conn.close()
                raise sqlite3.OperationalError(
                    f"Failed to apply encryption. Make sure SQLite3MultipleCiphers is installed. Error: {e}"
                ) from e
        
        # Standard SQLite optimizations
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -2000")
        
        return conn
    
    def is_encrypted(self, db_path: Path) -> bool:
        """Check if database file is encrypted."""
        if not db_path.exists():
            return False
        
        try:
            # Try to open without key
            test_conn = sqlite3.connect(str(db_path))
            test_conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            test_conn.close()
            return False  # Successfully opened = not encrypted
        except sqlite3.DatabaseError:
            return True   # Failed to open = likely encrypted
    
    def test_encryption_support(self) -> bool:
        """Test if SQLite encryption is available."""
        try:
            conn = sqlite3.connect(':memory:')
            conn.execute("PRAGMA key = 'test'")
            conn.close()
            return True
        except sqlite3.OperationalError:
            return False


# Global instance for easy access
encryption = SQLiteEncryption()