# Protocols API Reference

The `pydapter.protocols` module provides independent, composable interfaces for
models with specialized functionality.

## Installation

```bash
pip install pydapter
```

## Overview

Protocols in pydapter are **independent, composable interfaces** that can be
mixed and matched:

```text
Independent Protocols:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Identifiable  │  │    Temporal     │  │   Embeddable    │
│   (id: UUID)    │  │ (timestamps)    │  │ (content +      │
│                 │  │                 │  │  embedding)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│    Invokable    │  │ Cryptographical │
│ (execution      │  │ (hashing)       │
│  tracking)      │  │                 │
└─────────────────┘  └─────────────────┘

Event = Identifiable + Temporal + Embeddable + Invokable
```

Each protocol defines specific fields and can be used independently or combined
through multiple inheritance.

## Core Protocols

### Identifiable

**Module:** `pydapter.protocols.identifiable`

Provides unique identification using UUID.

**Protocol Interface:**

```python
@runtime_checkable
class Identifiable(Protocol):
    id: UUID
```

**Mixin Class:** `IdentifiableMixin`

- Provides UUID serialization to string
- Implements `__hash__` based on ID

**Usage:**

```python
from pydapter.protocols.identifiable import IdentifiableMixin
from pydantic import BaseModel

class User(BaseModel, IdentifiableMixin):
    name: str
    email: str

user = User(name="John Doe", email="john@example.com")
print(user.id)  # UUID field must be provided or use field defaults
```

### Temporal

**Module:** `pydapter.protocols.temporal`

Adds timestamp tracking capabilities.

**Protocol Interface:**

```python
@runtime_checkable
class Temporal(Protocol):
    created_at: datetime
    updated_at: datetime
```

**Mixin Class:** `TemporalMixin`

- `update_timestamp()`: Updates `updated_at` to current UTC time
- Provides datetime serialization to ISO format

**Usage:**

```python
from pydapter.protocols.temporal import TemporalMixin
from pydantic import BaseModel

class Article(BaseModel, TemporalMixin):
    title: str
    content: str

article = Article(title="Hello World", content="...")
article.update_timestamp()  # Updates updated_at field
```

### Embeddable

**Module:** `pydapter.protocols.embeddable`

Provides content and vector embedding support.

**Protocol Interface:**

```python
@runtime_checkable
class Embeddable(Protocol):
    content: str | None
    embedding: Embedding  # list[float]
```

**Mixin Class:** `EmbeddableMixin`

- `n_dim` property: Returns embedding dimensions
- `parse_embedding_response()`: Parses various embedding API response formats

**Usage:**

```python
from pydapter.protocols.embeddable import EmbeddableMixin
from pydantic import BaseModel

class Document(BaseModel, EmbeddableMixin):
    title: str

doc = Document(title="AI Research")
doc.content = "Machine learning research paper"
doc.embedding = [0.1, 0.2, 0.3, ...]
print(doc.n_dim)  # Returns embedding length
```

### Invokable

**Module:** `pydapter.protocols.invokable`

Enables asynchronous execution with state tracking.

**Protocol Interface:**

```python
@runtime_checkable
class Invokable(Protocol):
    request: dict | None
    execution: Execution
    _handler: Callable | None
    _handler_args: tuple[Any, ...]
    _handler_kwargs: dict[str, Any]
```

**Mixin Class:** `InvokableMixin`

- `invoke()`: Executes the handler and tracks execution state
- `has_invoked` property: Returns True if execution completed or failed
- Private attributes for handler management

**Usage:**

```python
from pydapter.protocols.invokable import InvokableMixin
from pydapter.fields.execution import Execution
from pydantic import BaseModel, PrivateAttr

class Task(BaseModel, InvokableMixin):
    name: str
    execution: Execution
    _handler: callable = PrivateAttr()
    _handler_args: tuple = PrivateAttr(default=())
    _handler_kwargs: dict = PrivateAttr(default_factory=dict)

async def process_data():
    return {"result": "success"}

task = Task(name="Process", execution=Execution())
task._handler = process_data
await task.invoke()
print(task.execution.status)  # ExecutionStatus.COMPLETED
```

### Cryptographical

**Module:** `pydapter.protocols.cryptographical`

Provides content hashing capabilities.

**Protocol Interface:**

```python
@runtime_checkable
class Cryptographical(Protocol):
    content: JsonValue
    sha256: str | None = None
```

**Mixin Class:** `CryptographicalMixin`

- `hash_content()`: Generates SHA-256 hash of content

**Usage:**

```python
from pydapter.protocols.cryptographical import CryptographicalMixin
from pydantic import BaseModel

class SecureData(BaseModel, CryptographicalMixin):
    title: str
    content: str

data = SecureData(title="Secret", content="classified information")
data.hash_content()
print(data.sha256)  # SHA-256 hash of content
```

## Event Protocol

### Event

**Module:** `pydapter.protocols.event`

The Event class combines multiple protocols into a comprehensive event tracking
system.

**Inheritance:**

```python
class Event(_BaseEvent, IdentifiableMixin, InvokableMixin, TemporalMixin, EmbeddableMixin):
    # Combines all major protocols
```

**Event Fields (from BASE_EVENT_FIELDS):**

- `id`: Unique identifier (UUID, frozen)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `embedding`: Vector representation
- `execution`: Execution state tracking
- `request`: Request parameters (dict)
- `content`: Event content (str | dict | JsonValue | None)
- `event_type`: Event classification (str | None)

**Constructor:**

```python
def __init__(
    self,
    handler: Callable,
    handler_arg: tuple[Any, ...],
    handler_kwargs: dict[str, Any],
    **data,
):
```

**Usage:**

```python
from pydapter.protocols.event import Event

async def process_user_data(user_id: str):
    return {"user_id": user_id, "processed": True}

event = Event(
    handler=process_user_data,
    handler_arg=("user123",),
    handler_kwargs={},
    content="Processing user data",
    event_type="data_processing"
)

await event.invoke()
print(event.execution.status)  # ExecutionStatus.COMPLETED
```

### Event Decorator: as_event

**Function:** `as_event`

Transforms functions into event-tracked operations.

**Signature:**

```python
def as_event(
    *,
    event_type: str | None = None,
    request_arg: str | None = None,
    embed_content: bool = False,
    embed_function: Callable[..., Embedding] | None = None,
    adapt: bool = False,
    adapter: type[Adapter | AsyncAdapter] | None = None,
    content_parser: Callable | None = None,
    strict_content: bool = False,
    **kw
) -> Callable
```

**Basic Usage:**

```python
from pydapter.protocols.event import as_event

@as_event(event_type="api_call")
async def process_request(data: dict) -> dict:
    return {"result": "processed", "input": data}

# Returns an Event object
event = await process_request({"user_id": 123})
print(event.event_type)  # "api_call"
```

**Advanced Usage with Embedding and Persistence:**

```python
from pydapter.protocols.event import as_event
from pydapter.extras import AsyncPostgresAdapter

def my_embedding_function(text: str) -> list[float]:
    # Your embedding logic
    return [0.1, 0.2, 0.3]

@as_event(
    event_type="ml_inference",
    embed_content=True,
    embed_function=my_embedding_function,
    adapt=True,
    adapter=AsyncPostgresAdapter,
    content_parser=lambda response: response.get("prediction"),
    database_url="postgresql://..."
)
async def run_model(input_data):
    prediction = {"prediction": "positive", "confidence": 0.95}
    return prediction

# Event is automatically created, embedded, and stored
event = await run_model({"text": "This is great!"})
```

## Protocol Composition

### Multiple Protocol Inheritance

Protocols are designed to be composed through multiple inheritance:

```python
from pydapter.protocols import (
    IdentifiableMixin,
    TemporalMixin,
    EmbeddableMixin,
    CryptographicalMixin
)
from pydantic import BaseModel

# Combine multiple protocols
class RichDocument(
    BaseModel,
    IdentifiableMixin,     # Adds: id
    TemporalMixin,         # Adds: created_at, updated_at
    EmbeddableMixin,       # Adds: content, embedding
    CryptographicalMixin   # Adds: sha256
):
    title: str
    category: str

# Use all protocol features
doc = RichDocument(
    title="Research Paper",
    category="AI",
    content="Deep learning research...",
    embedding=[0.1, 0.2, 0.3]
)

doc.update_timestamp()    # Temporal
doc.hash_content()        # Cryptographical
print(doc.n_dim)          # Embeddable
print(doc.id)             # Identifiable
```

### Selective Protocol Usage

Use only the protocols you need:

```python
# Just identification and timestamps
class SimpleEvent(BaseModel, IdentifiableMixin, TemporalMixin):
    action: str
    user_id: str

# Just embedding capability
class EmbeddedText(BaseModel, EmbeddableMixin):
    text: str

# Just execution tracking
class ExecutableTask(BaseModel, InvokableMixin):
    task_name: str
    execution: Execution
```

## Field Integration

Protocols integrate with the `pydapter.fields` system through pre-defined field
definitions:

```python
from pydapter.protocols.event import BASE_EVENT_FIELDS

# Standard event field definitions
BASE_EVENT_FIELDS = [
    ID_FROZEN.copy(name="id"),              # From pydapter.fields
    DATETIME.copy(name="created_at"),       # From pydapter.fields
    DATETIME.copy(name="updated_at"),       # From pydapter.fields
    EMBEDDING.copy(name="embedding"),       # From pydapter.fields
    EXECUTION.copy(name="execution"),       # From pydapter.fields
    PARAMS.copy(name="request"),            # From pydapter.fields
    # ... additional fields
]
```

## Best Practices

### Protocol Selection

1. **Use Minimal Sets**: Only include protocols you actually need
2. **Composition Over Inheritance**: Prefer multiple protocol mixins over
   complex hierarchies
3. **Field Consistency**: Use standard field definitions from `pydapter.fields`

### Event Tracking

1. **Strategic Decoration**: Use `@as_event` for important business operations
2. **Content Management**: Implement robust content parsing for complex
   responses
3. **Error Handling**: Handle execution failures gracefully
4. **Performance**: Consider overhead for high-frequency operations

### Protocol Patterns

```python
# Pattern 1: Basic entity with tracking
class TrackedEntity(BaseModel, IdentifiableMixin, TemporalMixin):
    pass

# Pattern 2: AI/ML document
class AIDocument(BaseModel, IdentifiableMixin, TemporalMixin, EmbeddableMixin):
    pass

# Pattern 3: Executable event
class ExecutableEvent(BaseModel, IdentifiableMixin, TemporalMixin, InvokableMixin):
    pass

# Pattern 4: Full event (all protocols)
class FullEvent(Event):  # Already combines all protocols
    pass
```

## Migration Guide

When upgrading from previous versions:

1. **Protocol Independence**: Update code that assumed hierarchical inheritance
2. **Field Integration**: Migrate to standardized field definitions
3. **Event Composition**: Use Event class for comprehensive event tracking
4. **Mixin Usage**: Prefer mixin classes over protocol interfaces for
   implementation

For detailed migration instructions, see the
[Migration Guide](../migration_guide.md#protocols-and-fields).
