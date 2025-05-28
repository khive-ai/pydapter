# Async/Sync Patterns in Pydapter

## Architecture Decision

Pydapter provides **separate sync and async implementations** without mixing
concerns:

- **Sync**: `Adapter`, `AdapterRegistry`, `Adaptable`
- **Async**: `AsyncAdapter`, `AsyncAdapterRegistry`, `AsyncAdaptable`

**Benefits:**

- No async overhead in sync operations
- Clear separation of concerns
- Type safety in both contexts
- Simple, focused interfaces

## Core Async Components

### AsyncAdapter Protocol

```python
from pydapter.async_core import AsyncAdapter

class MyAsyncAdapter(AsyncAdapter[T]):
    obj_key = "my_async_format"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many=False, **kw) -> T | list[T]:
        # Async operations (HTTP, database, etc.)
        pass

    @classmethod
    async def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> Any:
        # Async output operations
        pass
```

### AsyncAdapterRegistry

```python
from pydapter.async_core import AsyncAdapterRegistry

async_registry = AsyncAdapterRegistry()
async_registry.register(MyAsyncAdapter)

result = await async_registry.adapt_from(MyModel, data, obj_key="my_async_format")
```

### AsyncAdaptable Mixin

```python
from pydapter.async_core import AsyncAdaptable

class MyModel(BaseModel, AsyncAdaptable):
    name: str
    value: int

MyModel.register_async_adapter(MyAsyncAdapter)
instance = await MyModel.adapt_from_async(data, obj_key="my_async_format")
```

## Common Async Patterns

### HTTP API Adapter

```python
class RestApiAdapter(AsyncAdapter[T]):
    obj_key = "rest_api"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        url = f"{obj['base_url']}/{obj['endpoint']}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

        if many:
            items = data.get("items", data) if isinstance(data, dict) else data
            return [subj_cls.model_validate(item) for item in items]
        return subj_cls.model_validate(data)
```

### Database Adapter

```python
class AsyncPostgresAdapter(AsyncAdapter[T]):
    obj_key = "async_postgres"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        conn = await asyncpg.connect(obj["connection_string"])
        try:
            if many:
                rows = await conn.fetch(obj["query"], *obj.get("params", []))
                return [subj_cls.model_validate(dict(row)) for row in rows]
            else:
                row = await conn.fetchrow(obj["query"], *obj.get("params", []))
                return subj_cls.model_validate(dict(row)) if row else None
        finally:
            await conn.close()
```

### Concurrent Operations

```python
class ConcurrentAdapter(AsyncAdapter[T]):
    obj_key = "concurrent"

    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        sources = obj["sources"]
        max_concurrent = kw.get("max_concurrent", 5)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(source):
            async with semaphore:
                # Fetch from individual source
                return await SomeAdapter.from_obj(subj_cls, source)

        results = await asyncio.gather(
            *[fetch_one(source) for source in sources],
            return_exceptions=True
        )

        # Filter successful results
        successful = [r for r in results if not isinstance(r, Exception)]
        return successful if many else (successful[0] if successful else None)
```

## Sharing Logic Between Sync/Async

Use mixins for shared transformation logic:

```python
class DataTransformationMixin:
    @staticmethod
    def normalize_data(data: dict) -> dict:
        return {
            "id": data.get("identifier") or data.get("id"),
            "name": (data.get("name") or "").strip(),
            "active": data.get("status") == "active",
        }

# Sync adapter
class MySyncAdapter(Adapter[T], DataTransformationMixin):
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        normalized = cls.normalize_data(obj)
        return subj_cls.model_validate(normalized)

# Async adapter using same logic
class MyAsyncAdapter(AsyncAdapter[T], DataTransformationMixin):
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        data = await cls._fetch_async_data(obj["url"])
        normalized = cls.normalize_data(data)
        return subj_cls.model_validate(normalized)
```

## Error Handling Patterns

### Timeout Management

```python
class TimeoutAwareAdapter(AsyncAdapter[T]):
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        timeout_seconds = kw.get("timeout", 30)

        try:
            async with asyncio.timeout(timeout_seconds):
                return await cls._fetch_data(obj, subj_cls)
        except asyncio.TimeoutError:
            raise ParseError(f"Operation timed out after {timeout_seconds}s")
```

### Retry Logic

```python
class RetryableAdapter(AsyncAdapter[T]):
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=False, **kw):
        max_retries = kw.get("max_retries", 3)

        for attempt in range(max_retries + 1):
            try:
                return await cls._attempt_fetch(subj_cls, obj)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise ParseError(f"Failed after {max_retries + 1} attempts: {e}")
```

## Testing Async Adapters

```python
@pytest.mark.asyncio
class TestAsyncAdapters:
    async def test_http_adapter(self, respx_mock):
        respx_mock.get("http://api.example.com/data").mock(
            return_value=httpx.Response(200, json={"name": "test"})
        )

        result = await RestApiAdapter.from_obj(
            MyModel, {"base_url": "http://api.example.com", "endpoint": "data"}
        )
        assert result.name == "test"

    async def test_timeout_handling(self):
        with pytest.raises(ParseError, match="timed out"):
            await TimeoutAwareAdapter.from_obj(MyModel, config, timeout=0.1)
```

## Key Tips for LLM Developers

### 1. Resource Management

```python
# ✓ Always use context managers
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()

# ✓ Proper cleanup
conn = await asyncpg.connect(connection_string)
try:
    result = await conn.fetch(query)
finally:
    await conn.close()
```

### 2. Concurrency Control

```python
# ✓ Use semaphore for rate limiting
semaphore = asyncio.Semaphore(max_concurrent)

async def process_item(item):
    async with semaphore:
        # Process item without overwhelming external services
        pass
```

### 3. Common Async Caveats

- **Context managers**: Always use `async with` for resource cleanup
- **Timeouts**: Set reasonable timeouts for external operations
- **Error handling**: Distinguish between retryable and non-retryable errors
- **Concurrency limits**: Use semaphores to avoid overwhelming external services
- **Testing**: Use `pytest.mark.asyncio` and mock async dependencies

### 4. Separation of Concerns

```python
# ✓ Keep sync and async adapters separate
class SyncAdapter(Adapter[T]): pass
class AsyncAdapter(AsyncAdapter[T]): pass

# ✗ Avoid mixing sync/async in same class
```

### 5. Performance Patterns

- Use `asyncio.gather()` for concurrent operations
- Implement connection pooling for database adapters
- Add circuit breakers for external service calls
- Use exponential backoff for retry logic

This dual-API approach ensures optimal performance and clear separation between
synchronous and asynchronous contexts.
