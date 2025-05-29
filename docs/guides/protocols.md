# Working with Pydapter Protocols

## Protocol + Mixin Pattern

Each protocol provides:

1. **Protocol**: Interface for type checking
2. **Mixin**: Implementation with behavior

```python
@runtime_checkable
class Identifiable(Protocol):
    id: UUID

class IdentifiableMixin:
    def __hash__(self) -> int:
        return hash(self.id)
```

## Available Protocols

### Identifiable

- **Purpose**: UUID-based identity management
- **Fields**: `id: UUID`
- **Methods**: `__hash__()`, UUID serialization
- **Usage**: Base for all tracked entities

### Temporal

- **Purpose**: Timestamp management
- **Fields**: `created_at: datetime`, `updated_at: datetime`
- **Methods**: `update_timestamp()`, ISO datetime serialization
- **Usage**: Audit trails, versioning

### Embeddable

- **Purpose**: Vector embeddings for ML/AI
- **Fields**: `content: str | None`, `embedding: list[float]`
- **Methods**: Content processing, embedding validation
- **Usage**: RAG systems, semantic search

### Event

- **Purpose**: Comprehensive event tracking
- **Inherits**: Combines Identifiable, Temporal, Embeddable
- **Usage**: Event sourcing, audit logs

## Composition Patterns

### Basic Composition

```python
class User(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    email: str
```

### Inheritance Order Matters

```python
# ✓ Correct: BaseModel first, dependency order for mixins
class Document(BaseModel, IdentifiableMixin, TemporalMixin, EmbeddableMixin):
    # Protocol fields first
    id: UUID
    created_at: datetime
    updated_at: datetime
    content: str | None = None
    embedding: list[float] = Field(default_factory=list)

    # Domain fields
    title: str
```

## Custom Protocol Creation

```python
@runtime_checkable
class Versionable(Protocol):
    version: int
    version_history: list[int]

class VersionableMixin:
    def increment_version(self) -> None:
        if hasattr(self, 'version'):
            self.version_history.append(self.version)
            self.version += 1
```

## Type Checking

### Static Type Checking

```python
def process_identifiable_items(items: list[Identifiable]) -> list[UUID]:
    return [item.id for item in items]
```

### Runtime Type Checking

```python
def safe_get_id(obj: object) -> UUID | None:
    if isinstance(obj, Identifiable):
        return obj.id
    return None
```

## Integration with Fields

```python
from pydapter.fields import ID_FROZEN, DATETIME

class AdvancedModel(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID = ID_FROZEN.field_info
    created_at: datetime = DATETIME.field_info
    updated_at: datetime = DATETIME.field_info
```

## Key Tips for LLM Developers

### 1. Protocol Contract Compliance

- Always implement all required protocol fields
- Use proper type annotations
- Test protocol compliance with `isinstance()`

### 2. Mixin Order

- `BaseModel` first
- Protocol mixins in dependency order
- Custom mixins last

### 3. Automatic Serialization

- `IdentifiableMixin`: UUID → string
- `TemporalMixin`: datetime → ISO string
- Use `model_dump_json()` for proper serialization

### 4. Common Patterns

```python
# Standard composition for entities
class Entity(BaseModel, IdentifiableMixin, TemporalMixin):
    pass

# Standard composition for ML content
class MLContent(BaseModel, IdentifiableMixin, EmbeddableMixin):
    pass

# Standard composition for events
class EventRecord(BaseModel, Event):  # Event includes all protocols
    pass
```

### 5. Testing Protocol Implementation

```python
def test_protocol_compliance(model_instance):
    assert isinstance(model_instance, Identifiable)
    assert hasattr(model_instance, 'id')
    assert callable(getattr(model_instance, '__hash__'))
```

This protocol system enables consistent, type-safe behavior composition across
your models while maintaining clean separation of concerns.
