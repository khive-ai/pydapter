# Creating Custom Adapters

## Adapter Interface

All adapters implement the `Adapter` protocol:

```python
from pydapter.core import Adapter
from typing import ClassVar, TypeVar, Any

T = TypeVar("T", bound=BaseModel)

class MyAdapter(Adapter[T]):
    obj_key: ClassVar[str] = "my_format"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many=False, **kw) -> T | list[T]:
        """Convert from external format to model"""
        pass

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> Any:
        """Convert from model to external format"""
        pass
```

## Basic Implementation Pattern

```python
from pydapter.exceptions import ParseError, ValidationError as AdapterValidationError

class YamlAdapter(Adapter[T]):
    obj_key = "yaml"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str | Path, /, *, many=False, **kw):
        try:
            # Handle input types
            text = obj.read_text() if isinstance(obj, Path) else obj

            # Parse format
            data = yaml.safe_load(text)

            # Validate and convert
            if many:
                return [subj_cls.model_validate(item) for item in data]
            return subj_cls.model_validate(data)

        except yaml.YAMLError as e:
            raise ParseError(f"Invalid YAML: {e}", source=str(obj)[:100])
        except ValidationError as e:
            raise AdapterValidationError(f"Validation failed: {e}", errors=e.errors())

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> str:
        items = subj if isinstance(subj, list) else [subj]
        payload = [item.model_dump() for item in items] if many else items[0].model_dump()
        return yaml.dump(payload, **kw)
```

## Error Handling

### Exception Hierarchy

- **`ParseError`**: Invalid format/data structure
- **`ValidationError`**: Model validation failures
- **`AdapterError`**: General adapter issues

### Error Context Pattern

```python
try:
    # Adapter logic
    pass
except ParseError:
    raise  # Re-raise pydapter exceptions
except ValidationError as e:
    raise AdapterValidationError("Validation failed", data=data, errors=e.errors())
except Exception as e:
    raise ParseError(f"Unexpected error: {e}", source=str(obj)[:100])
```

## Advanced Patterns

### Configuration Support

```python
class DatabaseAdapter(Adapter[T]):
    DEFAULT_CONFIG = {"batch_size": 1000, "timeout": 30}

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        config = {**cls.DEFAULT_CONFIG, **kw}
        # Use config for connection settings, timeouts, etc.
```

### Metadata Integration

```python
@classmethod
def to_obj(cls, subj: T | list[T], /, *, many=False, **kw):
    for field_name, field_info in subj.model_fields.items():
        extra = field_info.json_schema_extra or {}

        # Use field metadata for custom formatting
        if extra.get("db_column"):
            # Map to different column name
        if extra.get("vector_dim"):
            # Handle vector data specially
```

## Async Adapters

```python
from pydapter.async_core import AsyncAdapter

class HttpApiAdapter(AsyncAdapter[T]):
    obj_key = "http_api"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        url = obj["url"]

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        if many:
            return [subj_cls.model_validate(item) for item in data]
        return subj_cls.model_validate(data)
```

## Testing Strategy

```python
class TestMyAdapter:
    def test_roundtrip(self):
        """Test data survives roundtrip conversion"""
        original = MyModel(name="test", value=42)
        external = MyAdapter.to_obj(original)
        restored = MyAdapter.from_obj(MyModel, external)
        assert restored == original

    def test_error_handling(self):
        with pytest.raises(ParseError):
            MyAdapter.from_obj(MyModel, "invalid_data")
```

## Registry Integration

```python
from pydapter.core import AdapterRegistry

registry = AdapterRegistry()
registry.register(YamlAdapter)

# Use through registry
user = registry.adapt_from(User, yaml_data, obj_key="yaml")
```

## Key Tips for LLM Developers

### 1. Stateless Design

- Use `@classmethod` for all adapter methods
- No instance variables or shared state
- Thread-safe by design

### 2. Error Handling

- Always provide context in error messages
- Use specific exception types
- Include source data preview (truncated)

### 3. Input Validation

```python
# Validate input type and structure
if not isinstance(obj, expected_types):
    raise ParseError(f"Expected {expected_types}, got {type(obj)}")

# Handle edge cases
if obj is None:
    return [] if many else None
```

### 4. Configuration Patterns

```python
# Merge defaults with user config
config = {**cls.DEFAULT_CONFIG, **kw}

# Extract specific options
timeout = config.pop("timeout", 30)
batch_size = config.pop("batch_size", 1000)
```

### 5. Common Caveats

- **Many parameter**: Handle both single items and lists consistently
- **Empty inputs**: Return appropriate empty values
- **Path vs string**: Support both file paths and direct content
- **Async context**: Proper resource cleanup with context managers
- **Error propagation**: Re-raise pydapter exceptions, wrap others

### 6. Field Metadata Usage

```python
# Access field metadata for custom behavior
for field_name, field_info in model.model_fields.items():
    extra = field_info.json_schema_extra or {}
    if extra.get("custom_format"):
        # Apply custom formatting
```

This pattern ensures adapters integrate seamlessly with pydapter's ecosystem
while maintaining consistency and reliability.
