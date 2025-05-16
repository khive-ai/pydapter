# Pydapter Protocols

The `pydapter.protocols` module defines a set of protocol interfaces that form
the foundation of the pydapter system. These protocols establish consistent
patterns for object identification, time tracking, embedding generation,
invocation handling, and service interfaces.

## Protocol Hierarchy

The protocols in this module are organized in a hierarchical structure:

```
types.py
    ↓
identifiable.py
    ↓
temporal.py
    ↓
embedable.py   invokable.py   service.py
    ↘             ↓             ↙
           event.py
```

## Protocol Overview

| Protocol          | Purpose                                 | Key Features                               |
| ----------------- | --------------------------------------- | ------------------------------------------ |
| `types.py`        | Define foundational types and enums     | Embedding, ExecutionStatus, Execution, Log |
| `identifiable.py` | Provide unique identification           | UUID generation, serialization             |
| `temporal.py`     | Track creation and update times         | Timestamp management, updates              |
| `embedable.py`    | Support vector embeddings               | Embedding generation, content creation     |
| `invokable.py`    | Enable function invocation              | Execution tracking, error handling         |
| `service.py`      | Define service interfaces               | Request handling                           |
| `event.py`        | Combine capabilities for event tracking | Decoration, storage, embedding             |

## Comprehensive Test Coverage

All protocols in this module have comprehensive test coverage, ensuring they
behave as expected and maintain compatibility with the rest of the system. The
test suites can be found in the `tests/protocols/` directory.

Key aspects covered by tests:

- Protocol initialization and default values
- Method behavior and return values
- Error handling and edge cases
- Serialization and deserialization
- Integration with other protocols

## Implementing New Protocols

When implementing new protocols that extend the existing ones, follow these
guidelines:

### 1. Choose the Right Base Protocol

Select the appropriate base protocol based on the functionality you need:

- Need unique identification? Extend `Identifiable`
- Need timestamp tracking? Extend `Temporal`
- Need embedding generation? Extend `Embedable`
- Need invocation handling? Extend `Invokable`
- Need service functionality? Implement `Service`
- Need comprehensive event tracking? Extend `Event`

### 2. Follow Protocol Patterns

Maintain consistency with existing protocols:

- Use Pydantic models for data validation
- Implement field validators and serializers
- Use type hints for better IDE support
- Document all methods and attributes
- Provide sensible default values

### 3. Example: Creating a New Protocol

```python
from pydantic import BaseModel, Field
from pydapter.protocols.temporal import Temporal

class MyNewProtocol(Temporal):
    """My new protocol that extends Temporal."""

    my_field: str = Field(default="default value", description="Description of my field")

    def my_method(self) -> str:
        """Description of what my method does."""
        self.update_timestamp()  # Update the timestamp when the method is called
        return f"Processed: {self.my_field}"
```

### 4. Testing Your Protocol

Ensure your protocol has comprehensive tests:

- Test initialization with default and custom values
- Test all methods and properties
- Test error handling and edge cases
- Test integration with other protocols
- Maintain >80% test coverage

## Protocol Implementation Best Practices

1. **Keep Protocols Focused**: Each protocol should have a single responsibility
2. **Use Composition**: Combine protocols through inheritance or composition
3. **Validate Inputs**: Use Pydantic validators to ensure data integrity
4. **Document Everything**: Provide clear docstrings for all classes and methods
5. **Handle Errors Gracefully**: Implement proper error handling
6. **Maintain Backward Compatibility**: Avoid breaking changes to existing
   protocols
7. **Follow Type Hints**: Use proper type annotations for better IDE support
8. **Test Thoroughly**: Ensure comprehensive test coverage

## Protocol Usage Examples

### Using Identifiable

```python
from pydapter.protocols.identifiable import Identifiable

# Create an identifiable object
obj = Identifiable()
print(f"Object ID: {obj.id}")  # Automatically generated UUID
```

### Using Temporal

```python
from pydapter.protocols.temporal import Temporal

# Create a temporal object
obj = Temporal()
print(f"Created at: {obj.created_at}")
print(f"Updated at: {obj.updated_at}")

# Update the timestamp
obj.update_timestamp()
print(f"New updated at: {obj.updated_at}")
```

### Using Embedable

```python
from pydapter.protocols.embedable import Embedable

# Create an embedable object
obj = Embedable(content="This is some content to embed")

# Generate an embedding
await obj.generate_embedding()
print(f"Embedding dimension: {obj.n_dim}")
```

### Using Event Decorator

```python
from pydapter.protocols.event import as_event

# Create an event-tracked function
@as_event(embed_content=True, adapt=True)
async def my_function(request):
    return {"result": f"Processed {request['input']}"}

# Call the function
event = await my_function({"input": "test data"})
print(f"Event ID: {event.id}")
print(f"Event status: {event.execution.status}")
```

By following these guidelines and examples, you can effectively implement and
use protocols in the pydapter system.
