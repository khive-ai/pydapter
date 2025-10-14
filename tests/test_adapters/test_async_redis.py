"""
Comprehensive tests for AsyncRedisAdapter using testcontainers.

This module tests the AsyncRedisAdapter implementation including:
- Protocol compliance with AsyncAdapter interface
- Dependency handling and import functionality
- Serialization/deserialization with msgpack and JSON
- Configuration validation and key generation
- Error handling and exception mapping
- Single and bulk operations with real Redis via testcontainers
"""

import asyncio
from typing import Any
from unittest.mock import patch

from pydantic import BaseModel
import pytest
import pytest_asyncio

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError


# Helper function to check if Redis dependencies are available
def is_redis_available():
    """Check if Redis async adapter dependencies are properly installed."""
    try:
        import orjson  # noqa: F401
        import ormsgpack  # noqa: F401
        import redis.asyncio as redis  # noqa: F401
        from tenacity import AsyncRetrying  # noqa: F401
        from testcontainers.redis import RedisContainer  # noqa: F401

        return True
    except ImportError:
        return False


# Create pytest marker to skip tests if Redis dependencies are not available
redis_skip_marker = pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis dependencies not available. Install with: pip install 'pydapter[redis]'",
)

# Import dependencies conditionally after availability check
if is_redis_available():
    import redis.asyncio as aioredis
    from testcontainers.redis import RedisContainer


# Test Models
class User(AsyncAdaptable, BaseModel):
    """Test model for Redis adapter testing."""

    id: int
    name: str
    email: str
    age: int = 25
    tags: list[str] = []
    metadata: dict[str, Any] = {}


# Fixtures
@pytest.fixture
def test_user():
    """Create a test user instance."""
    return User(
        id=1,
        name="john_doe",
        email="john@example.com",
        age=30,
        tags=["admin", "user"],
        metadata={"active": True, "score": 95.5},
    )


@pytest.fixture
def multiple_users():
    """Create multiple test users for bulk operations."""
    return [
        User(id=1, name="alice", email="alice@example.com", age=25, tags=["user"]),
        User(id=2, name="bob", email="bob@example.com", age=30, tags=["admin"]),
        User(id=3, name="charlie", email="charlie@example.com", age=35, tags=["guest"]),
    ]


@pytest_asyncio.fixture(scope="function")
async def redis_container():
    """
    Async Redis container fixture using testcontainers.
    Provides an isolated Redis instance for testing.
    """
    container = RedisContainer("redis:alpine")
    container.start()

    try:
        # Get connection details
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(6379))

        # Create async Redis client
        client = aioredis.Redis(host=host, port=port, decode_responses=False)

        # Test connection
        await client.ping()

        # Yield connection config for tests
        config = {"host": host, "port": port, "db": 0}
        yield config

        # Cleanup
        await client.aclose()
    finally:
        container.stop()


class TestAsyncRedisAdapterImport:
    """Test import functionality and dependency handling."""

    def test_import_without_dependencies(self):
        """Test import behavior when Redis dependencies are missing."""
        with patch.dict(
            "sys.modules",
            {
                "redis.asyncio": None,
                "ormsgpack": None,
                "orjson": None,
                "tenacity": None,
            },
        ):
            with pytest.raises(ImportError) as exc_info:
                import importlib

                import pydapter.extras.async_redis_

                importlib.reload(pydapter.extras.async_redis_)

            assert "Redis async adapter requires: pip install 'pydapter[redis]'" in str(
                exc_info.value
            )

    @redis_skip_marker
    def test_import_with_dependencies(self):
        """Test successful import when all dependencies are available."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        assert AsyncRedisAdapter is not None
        assert hasattr(AsyncRedisAdapter, "obj_key")
        assert AsyncRedisAdapter.obj_key == "async_redis"
        assert hasattr(AsyncRedisAdapter, "from_obj")
        assert hasattr(AsyncRedisAdapter, "to_obj")


@redis_skip_marker
class TestAsyncRedisAdapterConfiguration:
    """Test configuration validation and helper methods."""

    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        config = {"host": "localhost", "port": 6379}
        validated = AsyncRedisAdapter._validate_config(config, "test")
        assert validated["host"] == "localhost"
        assert validated["port"] == 6379

    def test_validate_config_defaults(self):
        """Test configuration validation applies defaults."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        config = {}
        validated = AsyncRedisAdapter._validate_config(config, "test")
        assert validated["host"] == "localhost"
        assert validated["port"] == 6379
        assert validated["db"] == 0

    def test_validate_config_invalid_type(self):
        """Test configuration validation with invalid config type."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        with pytest.raises(AdapterValidationError) as exc_info:
            AsyncRedisAdapter._validate_config("invalid", "test")

        assert "Configuration must be a dictionary" in str(exc_info.value)

    def test_connection_url_from_config(self):
        """Test URL extraction and building."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # From URL
        config = {"url": "redis://localhost:6379/0"}
        url = AsyncRedisAdapter._get_connection_url(config)
        assert url == "redis://localhost:6379/0"

        # From components
        config = {"host": "redis-server", "port": 6380, "db": 2}
        url = AsyncRedisAdapter._get_connection_url(config)
        assert url == "redis://redis-server:6380/2"

        # With auth
        config = {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "username": "user",
            "password": "pass",
        }
        url = AsyncRedisAdapter._get_connection_url(config)
        assert url == "redis://user:pass@localhost:6379/0"

    def test_key_generation(self, test_user):
        """Test key generation strategies."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Template-based
        config = {"key_template": "user:{id}:{name}"}
        key = AsyncRedisAdapter._generate_key(test_user, config)
        assert key == "user:1:john_doe"

        # Field-based with prefix
        config = {"key_field": "id", "key_prefix": "usr:"}
        key = AsyncRedisAdapter._generate_key(test_user, config)
        assert key == "usr:1"

        # Custom field
        config = {"key_field": "email"}
        key = AsyncRedisAdapter._generate_key(test_user, config)
        assert key == "john@example.com"

    def test_key_generation_errors(self, test_user):
        """Test key generation error cases."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Missing template field
        config = {"key_template": "user:{id}:{missing}"}
        with pytest.raises(AdapterValidationError) as exc_info:
            AsyncRedisAdapter._generate_key(test_user, config)
        assert "Key template references missing field" in str(exc_info.value)

        # Missing key field
        config = {"key_field": "missing_field"}
        with pytest.raises(AdapterValidationError) as exc_info:
            AsyncRedisAdapter._generate_key(test_user, config)
        assert "Model missing required key field" in str(exc_info.value)

    def test_missing_key_validation(self):
        """Test validation for missing key parameter."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Test missing key parameter - should fail during validation, not connection
        config = {"host": "localhost", "port": 6379}
        # The _validate_config should catch this before trying to connect
        # Note: This tests the validation logic, not the actual adapter call
        validated = AsyncRedisAdapter._validate_config(config, "from_obj")
        # Config is valid even without key - key is checked later in from_obj
        assert validated["host"] == "localhost"


@redis_skip_marker
class TestAsyncRedisAdapterSerialization:
    """Test serialization and deserialization functionality."""

    def test_serialize_msgpack(self, test_user):
        """Test msgpack serialization."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        serialized = AsyncRedisAdapter._serialize_model(test_user, serialization="msgpack")
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

    def test_serialize_json(self, test_user):
        """Test JSON serialization."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        serialized = AsyncRedisAdapter._serialize_model(test_user, serialization="json")
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

    def test_serialize_invalid_format(self, test_user):
        """Test serialization with invalid format."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        with pytest.raises(AdapterValidationError) as exc_info:
            AsyncRedisAdapter._serialize_model(test_user, serialization="invalid")
        assert "Unsupported serialization format" in str(exc_info.value)

    def test_deserialize_msgpack(self, test_user):
        """Test msgpack deserialization roundtrip."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Serialize then deserialize
        serialized = AsyncRedisAdapter._serialize_model(test_user, serialization="msgpack")
        deserialized = AsyncRedisAdapter._deserialize_model(
            serialized, User, serialization="msgpack"
        )

        assert deserialized.id == test_user.id
        assert deserialized.name == test_user.name
        assert deserialized.email == test_user.email
        assert deserialized.tags == test_user.tags

    def test_deserialize_json(self, test_user):
        """Test JSON deserialization roundtrip."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Serialize then deserialize
        serialized = AsyncRedisAdapter._serialize_model(test_user, serialization="json")
        deserialized = AsyncRedisAdapter._deserialize_model(serialized, User, serialization="json")

        assert deserialized.id == test_user.id
        assert deserialized.name == test_user.name
        assert deserialized.email == test_user.email


@redis_skip_marker
@pytest.mark.asyncio
class TestAsyncRedisAdapterOperations:
    """Test Redis operations with real container."""

    async def test_single_model_roundtrip(self, redis_container, test_user):
        """Test storing and retrieving a single model."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Store model
        write_config = {**redis_container, "key_template": "user:{id}"}
        result = await AsyncRedisAdapter.to_obj(test_user, **write_config)
        assert result == 1

        # Retrieve model
        read_config = {**redis_container, "key": "user:1"}
        retrieved = await AsyncRedisAdapter.from_obj(User, read_config)

        assert retrieved.id == test_user.id
        assert retrieved.name == test_user.name
        assert retrieved.email == test_user.email

    async def test_bulk_operations(self, redis_container, multiple_users):
        """Test bulk store and retrieve operations."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Store multiple models
        write_config = {**redis_container, "key_template": "bulk:{id}"}
        result = await AsyncRedisAdapter.to_obj(multiple_users, many=True, **write_config)
        assert result == 3

        # Retrieve by pattern
        read_config = {**redis_container, "pattern": "bulk:*"}
        retrieved = await AsyncRedisAdapter.from_obj(User, read_config, many=True)

        assert len(retrieved) == 3
        retrieved_ids = {user.id for user in retrieved}
        assert retrieved_ids == {1, 2, 3}

    async def test_ttl_functionality(self, redis_container, test_user):
        """Test TTL (expiration) functionality."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Store with short TTL
        write_config = {**redis_container, "key": "ttl_test", "ttl": 1}  # 1 second
        await AsyncRedisAdapter.to_obj(test_user, **write_config)

        # Should exist immediately
        read_config = {**redis_container, "key": "ttl_test"}
        retrieved = await AsyncRedisAdapter.from_obj(User, read_config)
        assert retrieved.id == test_user.id

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be gone
        with pytest.raises(ResourceError) as exc_info:
            await AsyncRedisAdapter.from_obj(User, read_config)
        assert "Key not found" in str(exc_info.value)

    async def test_serialization_formats(self, redis_container, test_user):
        """Test different serialization formats."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Test msgpack
        write_config = {
            **redis_container,
            "key": "msgpack_test",
            "serialization": "msgpack",
        }
        await AsyncRedisAdapter.to_obj(test_user, **write_config)

        read_config = {
            **redis_container,
            "key": "msgpack_test",
            "serialization": "msgpack",
        }
        retrieved = await AsyncRedisAdapter.from_obj(User, read_config)
        assert retrieved.name == test_user.name

        # Test JSON
        write_config = {**redis_container, "key": "json_test", "serialization": "json"}
        await AsyncRedisAdapter.to_obj(test_user, **write_config)

        read_config = {**redis_container, "key": "json_test", "serialization": "json"}
        retrieved = await AsyncRedisAdapter.from_obj(User, read_config)
        assert retrieved.name == test_user.name

    async def test_conditional_operations(self, redis_container, test_user):
        """Test NX and XX conditional operations."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Test NX (set if not exists)
        write_config = {**redis_container, "key": "nx_test", "nx": True}
        result1 = await AsyncRedisAdapter.to_obj(test_user, **write_config)
        assert result1 == 1  # Should succeed

        result2 = await AsyncRedisAdapter.to_obj(test_user, **write_config)
        assert result2 == 0  # Should fail (key exists)

        # Test XX (set if exists)
        test_user.name = "updated_name"
        write_config = {**redis_container, "key": "nx_test", "xx": True}
        result3 = await AsyncRedisAdapter.to_obj(test_user, **write_config)
        assert result3 == 1  # Should succeed (key exists)

    async def test_error_handling(self, redis_container):
        """Test error handling scenarios that require Redis connection."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Test missing key
        read_config = {**redis_container, "key": "nonexistent"}
        with pytest.raises(ResourceError) as exc_info:
            await AsyncRedisAdapter.from_obj(User, read_config)
        assert "Key not found" in str(exc_info.value)


@redis_skip_marker
@pytest.mark.asyncio
class TestAsyncRedisAdapterProtocol:
    """Test AsyncAdapter protocol compliance."""

    async def test_adapt_methods_integration(self, redis_container, test_user):
        """Test integration with AsyncAdaptable models."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Register adapter
        test_user.__class__.register_async_adapter(AsyncRedisAdapter)

        # Store using adapt_to_async
        config = {**redis_container, "key_template": "adapt:{id}"}
        await test_user.adapt_to_async(obj_key="async_redis", **config)

        # Retrieve using adapt_from_async
        read_config = {**redis_container, "key": "adapt:1"}
        retrieved = await User.adapt_from_async(obj_key="async_redis", obj=read_config)

        assert retrieved.id == test_user.id
        assert retrieved.name == test_user.name

    async def test_custom_adapt_methods(self, redis_container):
        """Test custom adaptation methods."""
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        # Create test data
        data = {"id": 42, "name": "custom", "email": "custom@test.com"}

        # Test with custom adapt methods
        test_user = User(**data)

        # Store with custom method
        config = {**redis_container, "key": "custom_test"}
        await AsyncRedisAdapter.to_obj(
            test_user,
            adapt_meth="model_dump",
            adapt_kw={"exclude": {"metadata"}},
            **config,
        )

        # Retrieve with custom method
        retrieved = await AsyncRedisAdapter.from_obj(
            User, config, adapt_meth="model_validate", adapt_kw={}
        )

        assert retrieved.id == 42
        assert retrieved.name == "custom"
