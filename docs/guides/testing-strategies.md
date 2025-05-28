# Testing Strategies for Pydapter

## Protocol Testing

### Protocol Compliance

```python
from pydapter.protocols import Identifiable, Temporal

def test_protocol_compliance():
    model = MyModel(id=uuid4(), created_at=datetime.now(), updated_at=datetime.now())

    # Runtime protocol checks
    assert isinstance(model, Identifiable)
    assert isinstance(model, Temporal)

    # Test mixin functionality
    original_updated = model.updated_at
    model.update_timestamp()
    assert model.updated_at > original_updated
```

## Adapter Testing

### Roundtrip Testing

```python
def test_adapter_roundtrip():
    """Test data survives roundtrip conversion"""
    original = MyModel(name="test", value=42)

    external = MyAdapter.to_obj(original)
    restored = MyAdapter.from_obj(MyModel, external)

    assert restored.name == original.name
    assert restored.value == original.value
```

### Error Handling

```python
def test_adapter_error_handling():
    """Test error scenarios"""
    with pytest.raises(ParseError, match="Invalid format"):
        MyAdapter.from_obj(MyModel, "invalid_data")

    with pytest.raises(ValidationError):
        MyAdapter.from_obj(MyModel, {"missing": "required_fields"})
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_adapter(respx_mock):
    """Test async adapters with mocked HTTP"""
    respx_mock.get("http://api.example.com/data").mock(
        return_value=httpx.Response(200, json={"name": "test"})
    )

    result = await MyAsyncAdapter.from_obj(MyModel, {"url": "http://api.example.com/data"})
    assert result.name == "test"
```

## Registry Testing

```python
def test_registry_operations():
    """Test adapter registry functionality"""
    registry = AdapterRegistry()
    registry.register(MyAdapter)

    # Test retrieval
    adapter = registry.get("my_adapter")
    assert adapter == MyAdapter

    # Test missing adapter
    with pytest.raises(AdapterNotFoundError):
        registry.get("nonexistent")
```

## Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
def test_field_validation_robustness(text_value):
    """Test field validators with random data"""
    field = Field(name="test", validator=lambda cls, v: v.strip())
    # Test edge cases with generated data
```

## Key Testing Patterns for LLM Developers

### 1. Test Fixtures

```python
@pytest.fixture
def sample_user():
    return User(
        id=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        name="Test User",
        email="test@example.com"
    )

@pytest.fixture
def user_registry():
    registry = AdapterRegistry()
    registry.register(JsonAdapter)
    registry.register(CsvAdapter)
    return registry
```

### 2. Mock External Dependencies

```python
# HTTP APIs
@pytest.fixture
def mock_api(respx_mock):
    respx_mock.get("http://api.example.com/users").mock(
        return_value=httpx.Response(200, json=[{"name": "John", "age": 30}])
    )

# Database connections
@pytest.fixture
def mock_db():
    with patch('asyncpg.connect') as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        yield mock_conn
```

### 3. Error Path Testing

```python
def test_all_error_scenarios():
    """Comprehensive error testing"""
    # Empty input
    with pytest.raises(ParseError, match="Empty.*content"):
        MyAdapter.from_obj(MyModel, "")

    # Invalid format
    with pytest.raises(ParseError, match="Invalid.*format"):
        MyAdapter.from_obj(MyModel, "invalid_format")

    # Validation failure
    with pytest.raises(ValidationError):
        MyAdapter.from_obj(MyModel, {"missing_required_field": True})
```

### 4. Async Testing Patterns

```python
@pytest.mark.asyncio
class TestAsyncOperations:
    async def test_concurrent_operations(self):
        """Test concurrent adapter operations"""
        tasks = [
            MyAsyncAdapter.from_obj(MyModel, {"id": i})
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10

    async def test_timeout_handling(self):
        """Test timeout scenarios"""
        with pytest.raises(ParseError, match="timed out"):
            await MyAsyncAdapter.from_obj(MyModel, config, timeout=0.01)
```

## Common Testing Caveats

### 1. Async Context

- Use `pytest.mark.asyncio` for async tests
- Mock external services (HTTP, database)
- Test timeout and retry logic

### 2. Protocol Mixins

- Test both interface and implementation
- Verify field serializers
- Check inheritance order effects

### 3. Registry Isolation

- Use fresh registries per test
- Clean up registered adapters
- Test adapter precedence

### 4. Error Context

- Verify specific exception types
- Check error message content
- Test error data preservation

## Testing Tips

- **Fixtures**: Use pytest fixtures for common setups
- **Mocking**: Mock external dependencies consistently
- **Error paths**: Test failures as thoroughly as success
- **Property-based**: Use Hypothesis for edge case discovery
- **Type safety**: Run mypy in CI to catch type errors
- **Isolation**: Ensure tests don't affect each other
