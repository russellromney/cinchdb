# Proposal: Unified Codegen Models Interface

## Summary

Implement a unified access point for generated models through a `CinchModels` container class, allowing developers to use `models = CinchModels(connect(...))` then `models.User(...)` instead of calling `User.set_connection()` individually for each model.

## Analysis: Is This Worth Implementing?

**Yes, this is a good idea** that significantly improves the developer experience with a cleaner, more opinionated architecture.

### Benefits

1. **Better Developer Experience**:
   - Single connection setup instead of per-model initialization
   - Clear namespace with IDE autocomplete (`models.User`, `models.Product`)
   - Consistent with the established `CinchDB` unified interface pattern
   - Natural tenant context passing without connection switching

2. **Cleaner Architecture**:
   - Database/branch defined at connection level (immutable context)
   - Tenant specified inline only when needed (mutable context)
   - Eliminates confusing model-level connection management
   - Single source of truth for connection parameters

3. **Better Separation of Concerns**:
   - Connection handles database/branch (infrastructure concerns)
   - Models handle tenant context (business logic concerns)
   - No ambiguity about which connection each model uses

4. **Future Flexibility**:
   - Foundation for model-level caching and connection pooling
   - Easier to implement cross-model operations
   - Natural place for model middleware/hooks
   - Could add model-level transaction support

### Drawbacks

1. **Breaking change** - requires migration from current approach
2. **Less flexible** - can't easily switch database/branch per model (this is actually a feature)
3. **Added abstraction layer** - but follows established CinchDB patterns
4. **Learning curve** - users need to understand the container pattern

### Trade-off Analysis

**Good trade-offs:**
- Loses individual model flexibility → Gains consistent connection management
- Loses backward compatibility → Gains cleaner, more maintainable architecture
- Adds container complexity → Eliminates per-model connection complexity

**Key insight:** The current approach of calling `set_connection()` on each model is error-prone and doesn't match how most ORMs work. The unified approach is more familiar to developers from other ecosystems (Django ORM, SQLAlchemy, etc.).

## Implementation Plan

### Phase 1: Core CinchModels Class

Create a container class in the codegen system:

```python
class CinchModels:
    """Unified interface for generated models."""
    
    def __init__(self, connection: CinchDB):
        """Initialize with a CinchDB connection.
        
        Args:
            connection: CinchDB instance (local or remote)
        """
        if not isinstance(connection, CinchDB):
            raise TypeError("CinchModels requires a CinchDB connection instance")
            
        self._connection = connection
        self._models = {}  # Lazy loaded model cache
        self._model_registry = {}  # Map of model names to classes
        self._tenant_override = None  # Optional tenant override
    
    def __getattr__(self, name: str):
        """Lazy load and return model class with connection set."""
        if name not in self._models:
            if name not in self._model_registry:
                raise AttributeError(f"Model '{name}' not found")
            
            model_class = self._model_registry[name]
            
            # Determine tenant to use (override or connection default)
            tenant = self._tenant_override or self._connection.tenant
            
            # Set connection using CinchDB's data manager or connection info
            if self._connection.is_local:
                model_class.set_connection(
                    self._connection.project_dir,
                    self._connection.database,
                    self._connection.branch,
                    tenant
                )
            else:
                # For remote connections, we'll need to enhance the model's set_connection
                # to accept a CinchDB instance and tenant override
                model_class.set_connection(self._connection, tenant_override=tenant)
            
            self._models[name] = model_class
        
        return self._models[name]
    
    def with_tenant(self, tenant: str) -> 'CinchModels':
        """Create models interface for a specific tenant with connection context override."""
        # Create a new CinchModels with same connection but different tenant context
        new_models = CinchModels(self._connection)
        new_models._tenant_override = tenant
        new_models._model_registry = self._model_registry
        return new_models
```

### Phase 2: Enhanced Codegen Generation

Update `CodegenManager._generate_python_models()` to:

1. **Generate the CinchModels class** in the output directory
2. **Create a model registry** in `__init__.py` that maps model names to classes
3. **Add a factory function** for easy instantiation

Generated `__init__.py` structure:
```python
"""Generated CinchDB models."""

from .cinch_models import CinchModels
from .user import User
from .product import Product

# Model registry for dynamic loading
_MODEL_REGISTRY = {
    'User': User,
    'Product': Product,
}

def create_models(connection: CinchDB) -> CinchModels:
    """Create unified models interface.
    
    Args:
        connection: CinchDB instance (local or remote)
        
    Returns:
        CinchModels container with all generated models
    """
    models = CinchModels(connection)
    models._model_registry = _MODEL_REGISTRY
    return models

__all__ = ['CinchModels', 'create_models', 'User', 'Product']
```

### Phase 3: Usage Examples

```python
# Unified approach
import cinchdb
from generated_models import create_models

# Connection defines database and branch
db = cinchdb.connect("mydb", branch="main")
models = create_models(db)

# Clean, discoverable API using connection's default tenant
users = models.User.select(age__gte=18)
user = models.User.create(name="Alice", email="alice@example.com")
products = models.Product.select(limit=10)

# Tenant specified inline when needed
customer_models = models.with_tenant("customer1")
customer_users = customer_models.User.select()
customer_orders = customer_models.Order.create(user_id="123", total=99.99)
```

```python
# Alternative: Direct model import (if needed for specific use cases)
from generated_models import User

# Models still available for direct import but require CinchModels container
# Individual model usage without container is no longer supported
```

## Implementation Notes

### Breaking Changes
- **Removes `set_connection()` method**: Generated models no longer have individual `set_connection()` methods
- **Requires CinchModels container**: All model operations must go through the `CinchModels` interface
- **Simplified architecture**: Models are only initialized through the container, eliminating connection management complexity

### Integration Points
- **Requires CinchDB instance**: Only accepts `CinchDB` connections, not raw `DataManager` instances
- **Works with both connection types**: Supports local (`cinchdb.connect()`) and remote (`cinchdb.connect_api()`) connections
- **Simple tenant context**: Implements `with_tenant()` for tenant-specific model operations
- **Follows established patterns**: Uses lazy loading pattern from `CinchDB` class
- **Simplified model architecture**: Generated models no longer need connection management methods

### Testing Strategy
- Unit tests for `CinchModels` class functionality
- Integration tests with generated models  
- Tenant context validation with `with_tenant()` method
- Remote connection testing with tenant overrides

## Recommendation

**Yes, implement this enhancement** despite the breaking change, because:

### Why This Is Worth The Breaking Change

1. **Architectural Improvement**: The current per-model `set_connection()` approach is fundamentally flawed - it's error-prone and doesn't scale well with multiple models

2. **Developer Experience**: The unified approach matches expectations from other ORMs and provides better discoverability and IDE support

3. **Future-Proofing**: This foundation enables advanced features like connection pooling, model-level transactions, and cross-model operations that would be difficult with the current approach

4. **Consistency**: Aligns perfectly with the established `CinchDB` unified interface pattern

5. **Cleaner Mental Model**: Database/branch as immutable infrastructure context, tenant as mutable business context

### Implementation Strategy

Since this is a breaking change, implement it as:
- **New major version** of the codegen system
- **Clear migration guide** for existing users  
- **Better defaults** - most users won't need tenant overrides

The cleaner architecture and improved developer experience justify the migration cost, especially since the codegen system is likely still in early adoption.