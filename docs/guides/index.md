# Pydapter Development Guides

## Overview

Pydapter is a protocol-driven data transformation framework that emphasizes
**stateless adapters**, **composable protocols**, **type safety**, and now a
**comprehensive field system** for building robust models.

## 🏗️ Field System (New in v0.3.0)

The field system provides powerful tools for model creation:

### Core Field Guides

- **[Fields Overview](fields.md)** - Advanced field descriptors, composition
  methods, and field templates
- **[Field Families](field-families.md)** - Pre-built field collections for
  common patterns (Entity, Audit, Soft Delete)
- **[Best Practices](fields-and-protocols-patterns.md)** - Comprehensive
  patterns for using fields with protocols

### Quick Example

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate
from pydapter.protocols import (
    create_protocol_model_class,
    IDENTIFIABLE,
    TEMPORAL
)

# Build models with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields(timezone_aware=True)  # id, created_at, updated_at
    .with_audit_fields()                      # created_by, updated_by, version
    .add_field("email", FieldTemplate(base_type=str))
    .build()
)

# Or create protocol-compliant models with behaviors
User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,
    TEMPORAL,
    email=FieldTemplate(base_type=str)
)

user = User(email="test@example.com")
user.update_timestamp()  # Method from TemporalMixin
```

## 🔌 Protocol System

Enhanced with type-safe constants and factory functions:

### Protocol Guides

- **[Protocols Overview](protocols.md)** - Deep dive into protocol system and
  mixins
- **[Protocol Patterns](fields-and-protocols-patterns.md)** - Common usage
  patterns and best practices

### What's New

- **Type-Safe Constants**: Use `IDENTIFIABLE`, `TEMPORAL` instead of strings
- **Factory Functions**: `create_protocol_model_class()` for one-step model creation
- **Mixin Helpers**: `combine_with_mixins()` to add behaviors to existing models

## 🏛️ Architecture & Implementation

### Core Concepts

- **[Architecture](architecture.md)** - Protocol-driven design, stateless
  adapters, dual sync/async APIs
- **[Creating Adapters](creating-adapters.md)** - Custom adapter patterns,
  error handling, metadata integration
- **[Async Patterns](async-patterns.md)** - Async adapters, concurrency
  control, resource management

### Testing & Examples

- **[Testing Strategies](testing-strategies.md)** - Protocol testing, adapter
  testing, async testing patterns
- **[End-to-End Backend](end-to-end-backend.md)** - Building backends with
  PostgreSQL, MongoDB, Neo4j

## Getting Started Flow

### 1. Understand the Architecture

Start with [Architecture](architecture.md) to grasp pydapter's core principles:

- Protocol + Mixin pattern for composable behaviors
- Stateless class methods for transformations
- Separate sync/async implementations

### 2. Define Your Models

Use [Protocols](protocols.md) to add standardized behaviors:

```python
class User(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    email: str
```

### 3. Configure Fields

Leverage [Fields](fields.md) for reusable, validated field definitions:

```python
from pydapter.fields import ID_FROZEN, DATETIME

class User(BaseModel):
    id: UUID = ID_FROZEN.field_info
    created_at: datetime = DATETIME.field_info
```

### 4. Create Adapters

Follow [Creating Adapters](creating-adapters.md) for data transformations:

```python
class YamlAdapter(Adapter[T]):
    obj_key = "yaml"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str, /, *, many=False, **kw):
        data = yaml.safe_load(obj)
        return subj_cls.model_validate(data)
```

### 5. Handle Async Operations

Use [Async Patterns](async-patterns.md) for async data sources:

```python
class ApiAdapter(AsyncAdapter[T]):
    obj_key = "api"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        async with aiohttp.ClientSession() as session:
            async with session.get(obj["url"]) as response:
                data = await response.json()
        return subj_cls.model_validate(data)
```

### 6. Test Your Implementation

Apply [Testing Strategies](testing-strategies.md) for robust validation:

```python
def test_adapter_roundtrip():
    original = User(name="test", email="test@example.com")
    external = YamlAdapter.to_obj(original)
    restored = YamlAdapter.from_obj(User, external)
    assert restored == original
```

## Key Design Patterns

### Protocol Composition

```python
# Standard entity pattern
class Entity(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID
    created_at: datetime
    updated_at: datetime

# ML content pattern
class MLContent(BaseModel, IdentifiableMixin, EmbeddableMixin):
    id: UUID
    content: str | None = None
    embedding: list[float] = Field(default_factory=list)
```

### Adapter Registry Pattern

```python
# Create registry
registry = AdapterRegistry()

# Register adapters
registry.register(JsonAdapter)
registry.register(YamlAdapter)
registry.register(CsvAdapter)

# Use through registry
user = registry.adapt_from(User, data, obj_key="json")
output = registry.adapt_to(user, obj_key="yaml")
```

### Repository Pattern

```python
class UserRepository:
    def __init__(self, registry: AsyncAdapterRegistry):
        self.registry = registry

    async def get_by_id(self, user_id: UUID) -> User | None:
        config = {"query": "SELECT * FROM users WHERE id = $1", "params": [user_id]}
        return await self.registry.adapt_from(User, config, obj_key="postgres")
```

## Common Use Cases

### 1. Multi-Format Data Processing

Handle JSON, CSV, YAML, XML with unified interface:

```python
registry = AdapterRegistry()
registry.register(JsonAdapter)
registry.register(CsvAdapter)
registry.register(YamlAdapter)

# Process any format
def process_data(data: str, format: str) -> list[User]:
    return registry.adapt_from(User, data, obj_key=format, many=True)
```

### 2. Database Abstraction

Work with multiple databases through consistent interface:

```python
# PostgreSQL for ACID transactions
users = await postgres_registry.adapt_from(User, postgres_config, obj_key="postgres")

# MongoDB for analytics
await mongo_registry.adapt_to(users, obj_key="mongo", collection="user_analytics")

# Neo4j for relationships
await neo4j_registry.adapt_to(users, obj_key="neo4j", relationship="KNOWS")
```

### 3. API Integration

Transform between internal models and external APIs:

```python
# Fetch from external API
external_users = await api_adapter.from_obj(ExternalUser, {"url": api_url}, many=True)

# Transform to internal format
internal_users = [InternalUser.model_validate(user.model_dump()) for user in external_users]

# Store in database
await db_adapter.to_obj(internal_users, many=True, table="users")
```

## Advanced Topics

### Field Metadata for Adapters

```python
VECTOR_FIELD = Field(
    name="embedding",
    annotation=list[float],
    json_schema_extra={
        "vector_dim": 768,
        "distance_metric": "cosine"
    }
)

# Adapters can use this metadata
class VectorDBAdapter(Adapter[T]):
    @classmethod
    def to_obj(cls, subj: T, **kw):
        for field_name, field_info in subj.model_fields.items():
            extra = field_info.json_schema_extra or {}
            if extra.get("vector_dim"):
                # Create vector column with specified dimension
                pass
```

### Custom Protocol Creation

```python
@runtime_checkable
class Auditable(Protocol):
    audit_log: list[str]

class AuditableMixin:
    def add_audit_entry(self, action: str) -> None:
        if not hasattr(self, 'audit_log'):
            self.audit_log = []
        self.audit_log.append(f"{datetime.now()}: {action}")
```

### Performance Optimization

```python
# Connection pooling for database adapters
class PooledDBAdapter(AsyncAdapter[T]):
    _pool: asyncpg.Pool = None

    @classmethod
    async def _get_pool(cls):
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(connection_string)
        return cls._pool

# Concurrent processing
async def process_multiple_sources(sources: list[dict]) -> list[T]:
    semaphore = asyncio.Semaphore(5)  # Limit concurrency

    async def process_one(source):
        async with semaphore:
            return await SomeAdapter.from_obj(MyModel, source)

    results = await asyncio.gather(*[process_one(s) for s in sources])
    return [r for r in results if r is not None]
```

## Best Practices Summary

### 1. Design Principles

- Use protocols for behavioral contracts
- Keep adapters stateless with class methods
- Compose behaviors through mixins
- Separate sync and async implementations

### 2. Error Handling

- Use specific exception types (`ParseError`, `ValidationError`)
- Provide detailed error context
- Test error paths thoroughly

### 3. Testing Strategy

- Test protocol compliance
- Verify adapter roundtrips
- Mock external dependencies
- Use property-based testing for edge cases

### 4. Performance

- Use connection pooling for databases
- Implement concurrency control with semaphores
- Add timeout and retry logic for external services
- Monitor and optimize hot paths

For detailed information on any topic, see the specific guide linked above.
