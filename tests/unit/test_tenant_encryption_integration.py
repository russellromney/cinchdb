"""Tests for tenant encryption integration."""

import pytest
import tempfile
import shutil
import sys
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.base import ConnectionContext
from cinchdb.core.initializer import init_project


class TestTenantEncryptionIntegration:
    """Test encryption integration with tenant creation and management."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir)
        
        # Initialize project
        init_project(project_root, database_name="testdb")
        
        yield project_root
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def tenant_manager(self, temp_project):
        """Create a TenantManager for testing."""
        return TenantManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main"))
    
    def test_create_tenant_generates_key_with_plugged(self, tenant_manager):
        """Test that tenant creation generates encryption key when plugged is available."""
        mock_key_manager = Mock()
        mock_key_manager.generate_tenant_key.return_value = "mock-encryption-key"
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = Mock(return_value=mock_key_manager)
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            # Create tenant - should generate encryption key
            tenant = tenant_manager.create_tenant("test_tenant", lazy=True)
            
            assert tenant.name == "test_tenant"
            
            # Verify key was generated with correct tenant ID
            mock_key_manager.generate_tenant_key.assert_called_once_with("testdb-main-test_tenant")
    
    def test_create_tenant_without_plugged(self, tenant_manager, caplog):
        """Test that tenant creation works without plugged (no key generation)."""
        # Set log level to DEBUG to capture debug messages
        caplog.set_level(logging.DEBUG, logger="cinchdb.managers.tenant")
        
        # No plugged module in sys.modules - import should fail
        if 'plugged' in sys.modules:
            del sys.modules['plugged']
        if 'plugged.tenant_key_manager' in sys.modules:
            del sys.modules['plugged.tenant_key_manager']
            
        # Create tenant - should work without encryption
        tenant = tenant_manager.create_tenant("test_tenant", lazy=True)
        
        assert tenant.name == "test_tenant"
        
        # Should log that plugged is not available
        assert "Plugged not available, skipping key generation" in caplog.text
    
    def test_create_tenant_key_generation_failure(self, tenant_manager, caplog):
        """Test that tenant creation continues even if key generation fails."""
        mock_key_manager = Mock()
        mock_key_manager.generate_tenant_key.side_effect = Exception("Key generation failed")
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = Mock(return_value=mock_key_manager)
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            # Create tenant - should still work despite key generation failure
            tenant = tenant_manager.create_tenant("test_tenant", lazy=True)
            
            assert tenant.name == "test_tenant"
            
            # Should log warning about failed key generation
            assert "Failed to generate encryption key for tenant test_tenant" in caplog.text
    
    def test_rotate_tenant_key_success(self, tenant_manager):
        """Test successful tenant key rotation."""
        mock_key_manager = Mock()
        mock_key_manager.generate_tenant_key.return_value = "new-encryption-key-v2"
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = Mock(return_value=mock_key_manager)
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            new_key = tenant_manager.rotate_tenant_key("test_tenant")
            
            assert new_key == "new-encryption-key-v2"
            mock_key_manager.generate_tenant_key.assert_called_once_with("testdb-main-test_tenant")
    
    def test_rotate_tenant_key_without_plugged(self, tenant_manager):
        """Test key rotation fails gracefully without plugged."""
        # No plugged module in sys.modules - import should fail
        if 'plugged' in sys.modules:
            del sys.modules['plugged']
        if 'plugged.tenant_key_manager' in sys.modules:
            del sys.modules['plugged.tenant_key_manager']
            
        with pytest.raises(ValueError, match="Plugged extension not available"):
            tenant_manager.rotate_tenant_key("test_tenant")
    
    def test_rotate_tenant_key_failure(self, tenant_manager):
        """Test key rotation handles failures properly."""
        mock_key_manager = Mock()
        mock_key_manager.generate_tenant_key.side_effect = Exception("Database error")
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = Mock(return_value=mock_key_manager)
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            with pytest.raises(ValueError, match="Failed to rotate key for tenant test_tenant"):
                tenant_manager.rotate_tenant_key("test_tenant")
    
    def test_tenant_id_format(self, tenant_manager):
        """Test that tenant ID format matches expected pattern."""
        mock_key_manager = Mock()
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = Mock(return_value=mock_key_manager)
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            tenant_manager.create_tenant("my_tenant", lazy=True)
            
            # Verify correct tenant ID format: database-branch-tenant
            expected_id = "testdb-main-my_tenant"
            mock_key_manager.generate_tenant_key.assert_called_once_with(expected_id)
    
    def test_key_manager_uses_metadata_db(self, tenant_manager):
        """Test that TenantKeyManager is initialized with correct metadata database."""
        mock_constructor = Mock()
        
        # Create a mock module and add it to sys.modules
        mock_plugged_module = Mock()
        mock_plugged_module.TenantKeyManager = mock_constructor
        
        with patch.dict('sys.modules', {'plugged': Mock(), 'plugged.tenant_key_manager': mock_plugged_module}):
            tenant_manager.create_tenant("test_tenant", lazy=True)
            
            # Verify TenantKeyManager was called with metadata_db
            mock_constructor.assert_called_once_with(tenant_manager.metadata_db)


