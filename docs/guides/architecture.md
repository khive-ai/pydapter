# Pydapter Architecture and Design Philosophy

## Core Principles

Pydapter follows **protocol-driven architecture** with **stateless
transformations** and **composition over inheritance**.

### 1. Protocol + Mixin Pattern

```python
@runtime_checkable
class Identifiable(Protocol):
    id: UUID

class IdentifiableMixin:
    def __hash__(self) -> int:
        return hash(self.id)
```

**Key Benefits:**

- Type safety without inheritance coupling
- Runtime validation when needed
- Composable behaviors

### 2. Stateless Class Methods

```python
class Adapter(Protocol[T]):
    obj_key: ClassVar[str]

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many=False, **kw) -> T | list[T]: ...

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> Any: ...
```

**Why Class Methods:**

- Thread safety (no shared state)
- No instantiation overhead
- Simple testing
- Clear interfaces

### 3. Dual Sync/Async APIs

Separate implementations without mixing concerns:

- **Sync**: `Adapter`, `AdapterRegistry`, `Adaptable`
- **Async**: `AsyncAdapter`, `AsyncAdapterRegistry`, `AsyncAdaptable`

**Benefits:**

- No async overhead in sync code
- Clear separation of concerns
- Type safety in both contexts

## Component Layers

### Core Layer

- **`Adapter`**: Transformation protocol
- **`AdapterRegistry`**: Adapter management
- **`Adaptable`**: Model mixin for adapter access

### Protocol Layer

- **`Identifiable`**: UUID-based identity
- **`Temporal`**: Timestamp management
- **`Embeddable`**: Vector embeddings
- **`Event`**: Event-driven patterns

### Field System

- **`Field`**: Advanced field descriptors
- **Pre-configured fields**: `ID_FROZEN`, `DATETIME`, `EMBEDDING`
- **Composition methods**: `as_nullable()`, `as_listable()`

### Adapter Ecosystem

- **Built-in**: JSON, CSV, TOML
- **Extended**: PostgreSQL, MongoDB, Neo4j, Qdrant, Weaviate

## Design Philosophy

### Composition Over Inheritance

```python
class Document(BaseModel, IdentifiableMixin, TemporalMixin):
    title: str
    content: str
```

### Progressive Complexity

```python
# Simple: Direct usage
person = JsonAdapter.from_obj(Person, json_data)

# Advanced: Registry-based
registry.adapt_from(Person, data, obj_key="json")
```

### Explicit Configuration

```python
# Clear interfaces, explicit parameters
person = JsonAdapter.from_obj(Person, data, many=False, strict=True)
```

## Extension Points

1. **Custom Adapters**: Implement `Adapter`/`AsyncAdapter` protocol
2. **Custom Protocols**: Extend existing or create new protocols
3. **Field Descriptors**: Domain-specific fields with `Field`
4. **Migration Adapters**: Schema evolution support
5. **Registry Extensions**: Specialized adapter collections

This architecture enables both simple use cases and complex production systems
through clear abstractions and composable components.
