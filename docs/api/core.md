# Core API Reference

The `pydapter.core` module provides the foundational adapter system for converting
between Pydantic models and various data formats. It implements a registry-based
pattern that enables stateless, bidirectional data transformations.

## Installation

```bash
pip install pydapter
```

## Overview

The core module establishes the fundamental concepts of pydapter:

- **Adapter Protocol**: Defines the interface for data conversion
- **Registry System**: Manages and discovers adapters
- **Adaptable Mixin**: Provides convenient model integration
- **Error Handling**: Comprehensive exception hierarchy for debugging

```text
Core Architecture:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Adapter     │  │ AdapterRegistry │  │    Adaptable    │
│   (Protocol)    │  │   (Manager)     │  │    (Mixin)      │
│                 │  │                 │  │                 │
│ from_obj()      │  │ register()      │  │ adapt_from()    │
│ to_obj()        │  │ get()           │  │ adapt_to()      │
│ obj_key         │  │ adapt_from()    │  │                 │
└─────────────────┘  │ adapt_to()      │  └─────────────────┘
                     └─────────────────┘
```

The system supports both synchronous and asynchronous operations through parallel
implementations in [`pydapter.core`](../api/core.md) and
[`pydapter.async_core`](../api/core.md#async-core-module).

## Core Protocols

### Adapter

**Module:** `pydapter.core`

Defines the interface for stateless data conversion between Pydantic models and
external formats.

**Protocol Interface:**

```python
@runtime_checkable
class Adapter(Protocol[T]):
    """Stateless conversion helper."""

    obj_key: ClassVar[str]  # Unique identifier for the adapter

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many: bool = False, **kw): ...

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw): ...
```

**Key Concepts:**

- **Stateless**: Adapters should not maintain internal state
- **Bidirectional**: Support both `from_obj` (import) and `to_obj` (export)
- **Type-safe**: Use generic typing for type safety
- **Batch Support**: Handle single items or collections via `many` parameter

**Implementation Example:**

```python
from pydapter.core import Adapter
from pydantic import BaseModel
import json

class JSONAdapter(Adapter):
    obj_key = "json"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str, /, *, many: bool = False, **kw):
        """Convert JSON string to Pydantic model(s)."""
        data = json.loads(obj)
        if many:
            return [subj_cls.model_validate(item) for item in data]
        return subj_cls.model_validate(data)

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw):
        """Convert Pydantic model(s) to JSON string."""
        if many or isinstance(subj, list):
            data = [item.model_dump() for item in subj]
        else:
            data = subj.model_dump()
        return json.dumps(data, **kw)

# Usage
class User(BaseModel):
    name: str
    email: str

json_data = '{"name": "John", "email": "john@example.com"}'
user = JSONAdapter.from_obj(User, json_data)
back_to_json = JSONAdapter.to_obj(user)
```

### AsyncAdapter

**Module:** `pydapter.async_core`

Asynchronous counterpart to the `Adapter` protocol for operations requiring async/await.

**Protocol Interface:**

```python
@runtime_checkable
class AsyncAdapter(Protocol[T]):
    """Stateless, **async** conversion helper."""

    obj_key: ClassVar[str]

    @classmethod
    async def from_obj(
        cls, subj_cls: type[T], obj: Any, /, *, many: bool = False, **kw
    ) -> T | list[T]: ...

    @classmethod
    async def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw) -> Any: ...
```

**Implementation Example:**

```python
from pydapter.async_core import AsyncAdapter
import aiohttp
import json

class HTTPAPIAdapter(AsyncAdapter):
    obj_key = "http_api"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: str, /, *, many: bool = False, **kw):
        """Fetch data from HTTP API and convert to model(s)."""
        async with aiohttp.ClientSession() as session:
            async with session.get(obj) as response:
                data = await response.json()
                if many:
                    return [subj_cls.model_validate(item) for item in data]
                return subj_cls.model_validate(data)

    @classmethod
    async def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw):
        """Convert model(s) to API payload."""
        if many or isinstance(subj, list):
            return [item.model_dump() for item in subj]
        return subj.model_dump()

# Usage
users = await HTTPAPIAdapter.from_obj(User, "https://api.example.com/users", many=True)
```

## Registry System

### AdapterRegistry

**Module:** `pydapter.core`

Manages adapter registration and provides convenient access methods.

**Class Interface:**

```python
class AdapterRegistry:
    def __init__(self) -> None: ...

    def register(self, adapter_cls: type[Adapter]) -> None: ...
    def get(self, obj_key: str) -> type[Adapter]: ...
    def adapt_from(self, subj_cls: type[T], obj, *, obj_key: str, **kw): ...
    def adapt_to(self, subj, *, obj_key: str, **kw): ...
```

**Usage:**

```python
from pydapter.core import AdapterRegistry

# Create registry
registry = AdapterRegistry()

# Register adapters
registry.register(JSONAdapter)
registry.register(CSVAdapter)

# Use via registry
user = registry.adapt_from(User, json_data, obj_key="json")
csv_data = registry.adapt_to(user, obj_key="csv")

# Direct adapter access
adapter_cls = registry.get("json")
user = adapter_cls.from_obj(User, json_data)
```

**Error Handling:**

The registry provides comprehensive error handling:

```python
from pydapter.exceptions import AdapterNotFoundError, AdapterError

try:
    user = registry.adapt_from(User, data, obj_key="unknown")
except AdapterNotFoundError as e:
    print(f"No adapter found: {e}")
except AdapterError as e:
    print(f"Adaptation failed: {e}")
```

### AsyncAdapterRegistry

**Module:** `pydapter.async_core`

Asynchronous version of `AdapterRegistry` for async adapters.

**Usage:**

```python
from pydapter.async_core import AsyncAdapterRegistry

# Create async registry
async_registry = AsyncAdapterRegistry()
async_registry.register(HTTPAPIAdapter)

# Use with async/await
users = await async_registry.adapt_from(User, api_url, obj_key="http_api", many=True)
```

## Adaptable Mixin

### Adaptable

**Module:** `pydapter.core`

Mixin class that integrates adapter functionality directly into Pydantic models.

**Class Interface:**

```python
class Adaptable:
    """Mixin that endows any Pydantic model with adapt-from / adapt-to."""

    _adapter_registry: ClassVar[AdapterRegistry | None] = None

    @classmethod
    def _registry(cls) -> AdapterRegistry: ...

    @classmethod
    def register_adapter(cls, adapter_cls: type[Adapter]) -> None: ...

    @classmethod
    def adapt_from(cls, obj, *, obj_key: str, **kw): ...

    def adapt_to(self, *, obj_key: str, **kw): ...
```

**Usage:**

```python
from pydapter.core import Adaptable
from pydantic import BaseModel

class User(BaseModel, Adaptable):
    name: str
    email: str
    age: int

# Register adapters for this model
User.register_adapter(JSONAdapter)
User.register_adapter(CSVAdapter)

# Use adapter methods directly on the model
user = User.adapt_from(json_data, obj_key="json")
csv_output = user.adapt_to(obj_key="csv")

# Class method for creating from external data
users = User.adapt_from(csv_file_content, obj_key="csv", many=True)
```

**Advanced Usage:**

```python
# Custom model with multiple adapters
class Product(BaseModel, Adaptable):
    id: str
    name: str
    price: float
    category: str

# Register multiple adapters
Product.register_adapter(JSONAdapter)
Product.register_adapter(XMLAdapter)
Product.register_adapter(DatabaseAdapter)

# Chain conversions
product = Product.adapt_from(xml_data, obj_key="xml")
json_data = product.adapt_to(obj_key="json")
database_record = product.adapt_to(obj_key="database")
```

## Exception Hierarchy

### Core Exceptions

**Module:** `pydapter.exceptions`

Comprehensive exception system for error handling and debugging.

#### AdapterError

Base exception for all pydapter errors.

```python
class AdapterError(Exception):
    """Base exception for all pydapter errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.message = message
        self.context = context  # Additional error context
```

**Usage:**

```python
from pydapter.exceptions import AdapterError

try:
    result = adapter.from_obj(Model, invalid_data)
except AdapterError as e:
    print(f"Error: {e.message}")
    print(f"Context: {e.context}")
```

#### ValidationError

Exception for data validation failures.

```python
class ValidationError(AdapterError):
    """Exception raised when data validation fails."""

    def __init__(self, message: str, data: Optional[Any] = None, **context: Any):
        super().__init__(message, **context)
        self.data = data  # The data that failed validation
```

#### TypeConversionError

Exception for type conversion failures.

```python
class TypeConversionError(ValidationError):
    """Exception raised when type conversion fails."""

    def __init__(
        self,
        message: str,
        source_type: Optional[type] = None,
        target_type: Optional[type] = None,
        field_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **context: Any,
    ): ...
```

#### AdapterNotFoundError

Exception when no adapter is registered for a given key.

```python
from pydapter.exceptions import AdapterNotFoundError

try:
    adapter = registry.get("nonexistent")
except AdapterNotFoundError as e:
    print(f"Adapter not found: {e}")
```

#### ConfigurationError

Exception for adapter configuration issues.

```python
from pydapter.exceptions import ConfigurationError

class BadAdapter:
    # Missing obj_key will raise ConfigurationError
    pass

try:
    registry.register(BadAdapter)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Advanced Usage Patterns

### Custom Adapter Development

Create specialized adapters for specific use cases:

```python
from pydapter.core import Adapter
from typing import Any, TypeVar
import yaml

T = TypeVar("T")

class YAMLAdapter(Adapter[T]):
    obj_key = "yaml"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str, /, *, many: bool = False, **kw):
        """Convert YAML string to Pydantic model(s)."""
        data = yaml.safe_load(obj)
        if many:
            return [subj_cls.model_validate(item) for item in data]
        return subj_cls.model_validate(data)

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw):
        """Convert Pydantic model(s) to YAML string."""
        if many or isinstance(subj, list):
            data = [item.model_dump() for item in subj]
        else:
            data = subj.model_dump()
        return yaml.dump(data, **kw)
```

### Adapter Composition

Combine multiple adapters for complex workflows:

```python
class DataPipeline:
    def __init__(self, model_cls, registry: AdapterRegistry):
        self.model_cls = model_cls
        self.registry = registry

    def transform(self, data, from_format: str, to_format: str, **kw):
        """Transform data from one format to another via Pydantic model."""
        # Parse input format to model
        model_instance = self.registry.adapt_from(
            self.model_cls, data, obj_key=from_format, **kw
        )

        # Convert model to output format
        return self.registry.adapt_to(
            model_instance, obj_key=to_format, **kw
        )

# Usage
pipeline = DataPipeline(User, registry)
json_data = pipeline.transform(csv_data, "csv", "json")
```

### Error Recovery

Implement robust error handling with fallbacks:

```python
def safe_adapt_from(model_cls, data, primary_key: str, fallback_key: str, registry):
    """Attempt adaptation with fallback on failure."""
    try:
        return registry.adapt_from(model_cls, data, obj_key=primary_key)
    except AdapterError as e:
        print(f"Primary adapter {primary_key} failed: {e}")
        try:
            return registry.adapt_from(model_cls, data, obj_key=fallback_key)
        except AdapterError as fallback_error:
            print(f"Fallback adapter {fallback_key} also failed: {fallback_error}")
            raise AdapterError(
                f"Both {primary_key} and {fallback_key} adapters failed",
                primary_error=str(e),
                fallback_error=str(fallback_error)
            )

# Usage
user = safe_adapt_from(User, data, "json", "yaml", registry)
```

## Best Practices

### Adapter Design

1. **Stateless Design**: Keep adapters stateless for thread safety
2. **Clear obj_key**: Use descriptive, unique keys for adapter identification
3. **Error Handling**: Provide meaningful error messages with context
4. **Type Safety**: Use proper type hints and validation
5. **Documentation**: Document expected input/output formats

### Performance Optimization

1. **Lazy Loading**: Register adapters only when needed
2. **Batch Processing**: Use `many=True` for collections
3. **Caching**: Cache registry lookups for frequently used adapters
4. **Memory Management**: Be mindful of memory usage with large datasets

### Registry Management

1. **Global Registry**: Use a single global registry for consistency
2. **Namespace Keys**: Use namespaced keys to avoid conflicts (e.g., "db.postgres")
3. **Validation**: Validate adapter implementations before registration
4. **Testing**: Test all registered adapters thoroughly

### Error Handling

1. **Specific Exceptions**: Use specific exception types for different error conditions
2. **Context Information**: Include relevant context in exception details
3. **Logging**: Log adapter errors for debugging
4. **Recovery Strategies**: Implement fallback mechanisms where appropriate

## Integration Examples

### Database Integration

```python
from pydapter.core import Adapter
import sqlite3

class SQLiteAdapter(Adapter):
    obj_key = "sqlite"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str, /, *, many: bool = False, **kw):
        """Load from SQLite database."""
        conn = sqlite3.connect(kw.get('database', ':memory:'))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if many:
            cursor.execute(f"SELECT * FROM {kw.get('table', subj_cls.__name__.lower())}")
            rows = cursor.fetchall()
            return [subj_cls.model_validate(dict(row)) for row in rows]
        else:
            cursor.execute(
                f"SELECT * FROM {kw.get('table', subj_cls.__name__.lower())} WHERE id = ?",
                (kw.get('id'),)
            )
            row = cursor.fetchone()
            return subj_cls.model_validate(dict(row)) if row else None
```

### Web API Integration

```python
from pydapter.async_core import AsyncAdapter
import httpx

class RESTAPIAdapter(AsyncAdapter):
    obj_key = "rest_api"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: str, /, *, many: bool = False, **kw):
        """Fetch from REST API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(obj, params=kw.get('params', {}))
            response.raise_for_status()
            data = response.json()

            if many:
                return [subj_cls.model_validate(item) for item in data]
            return subj_cls.model_validate(data)

    @classmethod
    async def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw):
        """Post to REST API."""
        url = kw.get('url')
        if not url:
            raise ValueError("URL required for REST API adapter")

        async with httpx.AsyncClient() as client:
            if many or isinstance(subj, list):
                data = [item.model_dump() for item in subj]
            else:
                data = subj.model_dump()

            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
```

## Migration Guide

When upgrading from previous versions:

1. **Adapter Interface**: Update custom adapters to use new protocol interface
2. **Error Handling**: Migrate to new exception hierarchy
3. **Registry Usage**: Use `AdapterRegistry` for better organization
4. **Async Support**: Consider migrating to async adapters for I/O operations
5. **Type Safety**: Add proper type hints to existing adapters

For detailed migration instructions, see the [Migration Guide](../migration_guide.md#core-system).

---

## Auto-generated API Reference

The following sections contain auto-generated API documentation:

## Core Module

::: pydapter.core
    options:
      show_root_heading: true
      show_source: true

## Async Core Module

::: pydapter.async_core
    options:
      show_root_heading: true
      show_source: true

## Exceptions

::: pydapter.exceptions
    options:
      show_root_heading: true
      show_source: true
