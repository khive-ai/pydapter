# Protocols API Reference

This page provides detailed API documentation for the `pydapter.protocols` module,
which implements composable interfaces for models with specialized functionality.

## Installation

```bash
pip install pydapter
```

## Module Overview

The protocols module provides independent, composable interfaces that can be mixed
and matched to add specialized behavior to Pydantic models:

```text
Protocol Architecture:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Identifiable  │  │    Temporal     │  │   Embeddable    │
│   (id: UUID)    │  │ (timestamps)    │  │ (content +      │
│                 │  │                 │  │  embedding)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Invokable    │  │ Cryptographical │  │   Auditable     │
│ (execution      │  │ (hashing)       │  │ (audit tracking)│
│  tracking)      │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐
│ SoftDeletable   │
│ (soft delete)   │
│                 │
└─────────────────┘

Event = Identifiable + Temporal + Embeddable + Invokable + Cryptographical
```

Each protocol defines specific fields and behavioral methods that can be used
independently or combined through multiple inheritance.

## Core Protocol Interfaces

### Protocol Definitions

The module provides runtime-checkable protocol interfaces that define contracts
for model behavior:

```python
from pydapter.protocols import (
    Identifiable,      # UUID-based identification
    Temporal,          # Creation and update timestamps
    Embeddable,        # Vector embeddings for ML
    Invokable,         # Async execution with state tracking
    Cryptographical,   # Content hashing capabilities
    Auditable,         # User tracking and versioning
    SoftDeletable,     # Soft deletion with restore
)
```

### Mixin Classes

Each protocol includes a corresponding mixin class that provides the implementation:

```python
from pydapter.protocols import (
    IdentifiableMixin,      # Hash implementation, UUID serialization
    TemporalMixin,          # update_timestamp() method
    EmbeddableMixin,        # n_dim property, embedding parsing
    InvokableMixin,         # invoke() method, execution tracking
    CryptographicalMixin,   # hash_content() method
    AuditableMixin,         # mark_updated_by() method
    SoftDeletableMixin,     # soft_delete(), restore() methods
)
```

## Usage Examples

### Basic Protocol Composition

```python
from pydapter.protocols import IdentifiableMixin, TemporalMixin
from pydantic import BaseModel

class User(BaseModel, IdentifiableMixin, TemporalMixin):
    name: str
    email: str

user = User(name="John", email="john@example.com")
user.update_timestamp()  # Method from TemporalMixin
print(user.id)           # UUID from IdentifiableMixin
```

### Event Protocol Usage

```python
from pydapter.protocols.event import Event

async def process_data(data: dict):
    return {"result": "processed", "input": data}

event = Event(
    handler=process_data,
    handler_arg=({"user_id": 123},),
    handler_kwargs={},
    event_type="data_processing"
)

await event.invoke()
print(event.execution.status)  # ExecutionStatus.COMPLETED
```

### Event Decorator

```python
from pydapter.protocols.event import as_event

@as_event(event_type="api_call")
async def process_request(data: dict) -> dict:
    return {"result": "processed", "input": data}

# Returns an Event object
event = await process_request({"user_id": 123})
print(event.event_type)  # "api_call"
```

## Factory Functions

### Protocol Model Creation

```python
from pydapter.protocols.factory import create_protocol_model_class
from pydapter.protocols.constants import IDENTIFIABLE, TEMPORAL

User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,  # Adds id field + behavior
    TEMPORAL,      # Adds timestamps + update_timestamp() method
    name=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str)
)
```

### Mixin Combination

```python
from pydapter.protocols.factory import combine_with_mixins

EnhancedUser = combine_with_mixins(
    BaseUser,
    ["identifiable", "temporal", "auditable"],
    name="EnhancedUser"
)
```

## Registry System

### Dynamic Protocol Registration

```python
from pydapter.protocols.registry import register_mixin, get_mixin_registry

# Register a custom protocol
class GeospatialMixin:
    def set_coordinates(self, lat: float, lng: float):
        self.latitude = lat
        self.longitude = lng

register_mixin("geospatial", GeospatialMixin)

# View all registered protocols
registry = get_mixin_registry()
print(list(registry.keys()))
# ['identifiable', 'temporal', 'embeddable', 'invokable',
#  'cryptographical', 'auditable', 'soft_deletable', 'geospatial']
```

## Field Integration

Protocols integrate with the field system through pre-defined field families:

```python
from pydapter.fields.protocol_families import ProtocolFieldFamilies

# Access protocol field definitions
entity_fields = ProtocolFieldFamilies.ENTITY        # id, created_at, updated_at
audit_fields = ProtocolFieldFamilies.AUDITABLE      # created_by, updated_by, version
soft_delete_fields = ProtocolFieldFamilies.SOFT_DELETABLE  # deleted_at, is_deleted
```

## Protocol Constants

```python
from pydapter.protocols.constants import (
    IDENTIFIABLE,
    TEMPORAL,
    EMBEDDABLE,
    INVOKABLE,
    CRYPTOGRAPHICAL,
    AUDITABLE,
    SOFT_DELETABLE,
    PROTOCOL_MIXINS,  # Maps protocol names to mixin classes
)
```

## Advanced Usage

### Multiple Protocol Inheritance

```python
from pydapter.protocols import (
    IdentifiableMixin,
    TemporalMixin,
    EmbeddableMixin,
    AuditableMixin,
    SoftDeletableMixin
)

class RichDocument(
    BaseModel,
    IdentifiableMixin,
    TemporalMixin,
    EmbeddableMixin,
    AuditableMixin,
    SoftDeletableMixin
):
    title: str
    content: str

doc = RichDocument(title="Report", content="Content")
doc.update_timestamp()       # Temporal
doc.hash_content()           # Cryptographical (if included)
doc.mark_updated_by("user")  # Auditable
doc.soft_delete()            # SoftDeletable
```

### Event with Embedding and Persistence

```python
from pydapter.protocols.event import as_event
from pydapter.extras import AsyncPostgresAdapter

@as_event(
    event_type="ml_inference",
    embed_content=True,
    embed_function=embedding_function,
    adapt=True,
    adapter=AsyncPostgresAdapter,
    database_url="postgresql://..."
)
async def run_model(input_data):
    return {"prediction": "positive", "confidence": 0.95}

# Event is automatically created, embedded, and stored
event = await run_model({"text": "This is great!"})
```

## Best Practices

### Protocol Selection

1. **Use Minimal Sets**: Only include protocols you actually need
2. **Composition Over Inheritance**: Prefer multiple protocol mixins
3. **Field Consistency**: Use standard field definitions from field families

### Performance Considerations

1. **Lazy Registration**: Register protocols only when needed
2. **Selective Composition**: Avoid unnecessary protocol overhead
3. **Event Decoration**: Consider performance impact for high-frequency operations

---

## Auto-generated API Reference

The following sections contain auto-generated API documentation for all protocol modules:

## Core Protocols

### Identifiable

::: pydapter.protocols.identifiable
    options:
      show_root_heading: true
      show_source: true

### Temporal

::: pydapter.protocols.temporal
    options:
      show_root_heading: true
      show_source: true

### Embeddable

::: pydapter.protocols.embeddable
    options:
      show_root_heading: true
      show_source: true

### Invokable

::: pydapter.protocols.invokable
    options:
      show_root_heading: true
      show_source: true

### Cryptographical

::: pydapter.protocols.cryptographical
    options:
      show_root_heading: true
      show_source: true

### Auditable

::: pydapter.protocols.auditable
    options:
      show_root_heading: true
      show_source: true

### Soft Deletable

::: pydapter.protocols.soft_deletable
    options:
      show_root_heading: true
      show_source: true

## Event System

### Event Class

::: pydapter.protocols.event.Event
    options:
      show_root_heading: true
      show_source: true

### Event Decorator

::: pydapter.protocols.event.as_event
    options:
      show_root_heading: true
      show_source: true

## Factory and Utilities

### Protocol Factory

::: pydapter.protocols.factory
    options:
      show_root_heading: true
      show_source: true

### Protocol Registry

::: pydapter.protocols.registry
    options:
      show_root_heading: true
      show_source: true

### Protocol Constants

::: pydapter.protocols.constants
    options:
      show_root_heading: true
      show_source: true

### Protocol Types

::: pydapter.protocols.types
    options:
      show_root_heading: true
      show_source: true

### Protocol Utilities

::: pydapter.protocols.utils
    options:
      show_root_heading: true
      show_source: true
