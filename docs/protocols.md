# Protocols Module

The Protocols module provides a set of standardized interfaces that can be used
to add common capabilities to your models. These protocols follow a clean
inheritance hierarchy and are designed to be composable, allowing you to mix and
match capabilities as needed.

## Installation

The Protocols module is available as an optional dependency. To use it, install
pydapter with the `protocols` extra:

```bash
pip install pydapter[protocols]
```

This will install the required dependencies, including `typing-extensions`.

## Available Protocols

The Protocols module provides the following interfaces:

- **Identifiable**: Unique identification using UUID
- **Temporal**: Creation and update timestamps
- **Embeddable**: Vector embeddings for ML applications
- **Invokable**: Function execution with state tracking
- **Event**: Comprehensive event tracking (combines multiple protocols)
- **Auditable**: User tracking and versioning for audit trails
- **SoftDeletable**: Soft deletion with restore capabilities
- **Cryptographical**: Content hashing capabilities

### Identifiable

The `Identifiable` protocol provides a unique identifier for objects. It's the
foundation of the protocol hierarchy.

**Key features:**

- Automatic UUID generation
- String serialization of UUIDs
- UUID validation
- Hash implementation for use in sets and dictionaries

```python
from pydapter.protocols import Identifiable

class User(Identifiable):
    name: str
    email: str

# UUID is automatically generated
user = User(name="John Doe", email="john@example.com")
print(f"User ID: {user.id}")  # User ID: 3f7c8e9a-1d2b-4c3d-8e7f-5a6b7c8d9e0f
```

### Temporal

The `Temporal` protocol adds creation and update timestamps to objects.

**Key features:**

- Automatic creation timestamp
- Automatic update timestamp
- Method to manually update the timestamp
- ISO-8601 serialization of timestamps

```python
from pydapter.protocols import Identifiable, Temporal

class User(Identifiable, Temporal):
    name: str
    email: str

# Timestamps are automatically set
user = User(name="John Doe", email="john@example.com")
print(f"Created at: {user.created_at}")  # Created at: 2025-05-16T15:30:00+00:00
print(f"Updated at: {user.updated_at}")  # Updated at: 2025-05-16T15:30:00+00:00

# Update the timestamp manually
user.name = "Jane Doe"
user.update_timestamp()
print(f"Updated at: {user.updated_at}")  # Updated at: 2025-05-16T15:31:00+00:00
```

### Embedable

The `Embedable` protocol adds support for vector embeddings, which are commonly
used in machine learning and natural language processing applications.

**Key features:**

- Storage for embedding vectors
- Content field for the text to be embedded
- Dimension calculation
- Support for various embedding formats (list, JSON string)

```python
from pydapter.protocols import Identifiable, Temporal, Embedable

class Document(Identifiable, Temporal, Embedable):
    title: str

# Create a document with an embedding
document = Document(
    title="Sample Document",
    content="This is a sample document for embedding.",
    embedding=[0.1, 0.2, 0.3, 0.4]
)

print(f"Embedding dimensions: {document.n_dim}")  # Embedding dimensions: 4

# Embeddings can also be provided as a JSON string
document2 = Document(
    title="Another Document",
    content="This is another sample document.",
    embedding="[0.5, 0.6, 0.7, 0.8]"
)
```

### Invokable

The `Invokable` protocol adds function invocation capabilities with execution
tracking.

**Key features:**

- Execution status tracking
- Duration measurement
- Error handling
- Response storage

```python
import asyncio
from pydapter.protocols import Identifiable, Temporal, Invokable

class APICall(Identifiable, Temporal, Invokable):
    endpoint: str

    async def fetch_data(self):
        # Simulate API call
        await asyncio.sleep(1)
        return {"data": "Sample response"}

# Create an API call
api_call = APICall(endpoint="/api/data")
api_call._invoke_function = api_call.fetch_data

# Execute the call
await api_call.invoke()

print(f"Status: {api_call.execution.status}")  # Status: completed
print(f"Duration: {api_call.execution.duration:.2f}s")  # Duration: 1.00s
print(f"Response: {api_call.execution.response}")  # Response: {'data': 'Sample response'}
```

### Event

The `Event` protocol combines the capabilities of `Identifiable`, `Temporal`,
`Embedable`, and `Invokable` to provide a comprehensive event tracking
interface.

```python
from pydapter.protocols import Event

class LogEvent(Event):
    event_type: str

    async def process(self):
        # Process the event
        return {"processed": True}

# Create an event
log_event = LogEvent(
    event_type="system_log",
    content="User logged in",
)
log_event._invoke_function = log_event.process

# Execute the event
await log_event.invoke()

print(f"Event ID: {log_event.id}")
print(f"Created at: {log_event.created_at}")
print(f"Status: {log_event.execution.status}")
```

### Auditable

The `Auditable` protocol adds user tracking and versioning capabilities for audit trails.

**Key features:**

- Tracks who created the entity (`created_by`)
- Tracks who last updated the entity (`updated_by`)
- Version number for optimistic locking
- Integration with temporal updates

```python
from pydapter.protocols import Identifiable, Temporal
from pydapter.protocols.auditable import AuditableMixin

class AuditedDocument(Identifiable, Temporal, AuditableMixin):
    title: str
    content: str
    created_by: str | None = None
    updated_by: str | None = None
    version: int = 1

# Create and audit a document
doc = AuditedDocument(
    title="Confidential Report",
    content="Sensitive information",
    created_by="admin"
)

# Update with audit trail
doc.content = "Updated content"
doc.mark_updated_by("editor123")
print(f"Version: {doc.version}")      # Version: 2
print(f"Updated by: {doc.updated_by}") # Updated by: editor123
```

### SoftDeletable

The `SoftDeletable` protocol provides soft deletion capabilities, allowing entities to
be marked as deleted without permanently removing them.

**Key features:**

- Marks deletion with timestamp (`deleted_at`)
- Boolean flag for deletion status (`is_deleted`)
- Restore capability for recovering deleted entities
- Preserves data for audit and recovery purposes

```python
from pydapter.protocols import Identifiable
from pydapter.protocols.soft_deletable import SoftDeletableMixin

class SoftDeletableUser(Identifiable, SoftDeletableMixin):
    name: str
    email: str
    deleted_at: datetime | None = None
    is_deleted: bool = False

# Create and soft delete a user
user = SoftDeletableUser(name="John Doe", email="john@example.com")

# Soft delete the user
user.soft_delete()
print(f"Deleted: {user.is_deleted}")    # Deleted: True
print(f"Deleted at: {user.deleted_at}") # Deleted at: 2023-10-01T12:00:00+00:00

# Restore the user
user.restore()
print(f"Deleted: {user.is_deleted}")    # Deleted: False
print(f"Deleted at: {user.deleted_at}") # Deleted at: None
```

## Protocol Registry

The protocol registry system allows for dynamic registration and discovery of protocol mixins.

**Key features:**

- Dynamic mixin registration
- Extensible protocol system
- Runtime protocol discovery
- Custom protocol support

```python
from pydapter.protocols.registry import register_mixin, get_mixin_registry

# Define a custom protocol mixin
class GeospatialMixin:
    def set_coordinates(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

# Register the custom mixin
register_mixin("geospatial", GeospatialMixin)

# View all registered protocols
registry = get_mixin_registry()
print(list(registry.keys()))
# Output: ['identifiable', 'temporal', 'embeddable', 'invokable', 'cryptographical', 'auditable', 'soft_deletable', 'geospatial']
```

## Protocol Inheritance Hierarchy

The protocols follow a hierarchical structure:

```text
Identifiable
    │
    ├── Temporal
    │       │
    │       ├── Embedable
    │       │
    │       └── Invokable
    │               │
    │               └── Event
    │
    └── Other custom protocols...
```

This design allows you to compose protocols as needed, inheriting only the
capabilities required for your specific use case.

## Best Practices

### Composing Protocols

When using multiple protocols, inherit them in the correct order to ensure
proper initialization:

```python
# Correct order
class MyModel(Identifiable, Temporal, Embedable):
    pass

# Incorrect order - may cause initialization issues
class MyModel(Embedable, Temporal, Identifiable):
    pass
```

### Custom Content Creation

The `Embedable` protocol allows you to customize how content is created by
overriding the `create_content` method:

```python
class Document(Identifiable, Temporal, Embedable):
    title: str
    body: str

    def create_content(self):
        return f"{self.title}\n\n{self.body}"
```

### Custom Invocation Functions

When using the `Invokable` protocol, you need to set the `_invoke_function`
attribute to the function you want to invoke:

```python
async def fetch_data(endpoint):
    # Fetch data from endpoint
    return {"data": "Sample response"}

api_call = APICall(endpoint="/api/data")
api_call._invoke_function = fetch_data
api_call._invoke_args = [api_call.endpoint]  # Arguments to pass to the function
```

## Type Checking

The protocols module is designed to work well with static type checkers like
mypy. The protocols are defined using `typing_extensions.Protocol` and are
marked as `runtime_checkable`, allowing for both static and runtime type
checking.

```python
from typing import List
from pydapter.protocols import Identifiable

def process_identifiables(items: List[Identifiable]):
    for item in items:
        print(f"Processing item {item.id}")

# This will pass type checking
process_identifiables([User(name="John"), Document(title="Sample")])
```

## Error Handling

If you try to import protocols without the required dependencies, you'll get a
clear error message:

```text
ImportError: The 'protocols' feature requires the 'typing_extensions' package. Install it with: pip install pydapter[protocols]
```

This helps guide users to install the correct dependencies.

## Advanced Usage

### Custom Protocol Extensions

You can create your own protocols by extending the existing ones:

```python
from pydapter.protocols import Identifiable, Temporal
from pydantic import Field

class Versionable(Temporal):
    """Protocol for objects that support versioning."""

    version: int = Field(default=1)

    def increment_version(self):
        """Increment the version and update the timestamp."""
        self.version += 1
        self.update_timestamp()

class Document(Identifiable, Temporal, Versionable):
    title: str
    content: str
```

### Integration with Adapters

The protocols can be used with pydapter adapters to provide standardized
interfaces for data access:

```python
from pydapter.core import Adapter
from pydapter.protocols import Identifiable, Temporal

class User(Identifiable, Temporal):
    name: str
    email: str

# Create an adapter for a list of users
users = [
    User(name="John Doe", email="john@example.com"),
    User(name="Jane Doe", email="jane@example.com")
]
adapter = Adapter(users)

# Query by ID
user = adapter.get(id="3f7c8e9a-1d2b-4c3d-8e7f-5a6b7c8d9e0f")
```
