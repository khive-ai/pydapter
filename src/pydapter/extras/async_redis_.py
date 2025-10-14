"""
AsyncRedisAdapter - Asynchronous Redis adapter for pydapter.

This adapter provides async methods to:
- Store and retrieve Pydantic models from Redis using msgpack or JSON serialization
- Handle async Redis operations with connection pooling and retry logic
- Support single key operations and pattern-based bulk operations
- Comprehensive error handling with pydapter exception mapping
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

try:
    import orjson
    import ormsgpack
    import redis.asyncio as redis
    from redis.asyncio import Redis as AsyncRedis
    from tenacity import (
        AsyncRetrying,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
except ImportError as e:
    raise ImportError("Redis async adapter requires: pip install 'pydapter[redis]'") from e

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..async_core import AsyncAdapter, AsyncAdapterBase
from ..core import dispatch_adapt_meth
from ..exceptions import ConnectionError, PydapterError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)

__all__ = (
    "AsyncRedisAdapter",
    "AsyncRedis",
)


class AsyncRedisAdapter(AsyncAdapterBase, AsyncAdapter[T]):
    """
    Asynchronous Redis adapter for converting between Pydantic models and Redis data.

    This adapter provides async methods to:
    - Store Pydantic models as serialized data in Redis
    - Retrieve and deserialize Redis data back to Pydantic models
    - Handle async Redis operations with connection pooling
    - Support both msgpack (performance) and JSON (compatibility) serialization
    - Comprehensive retry logic for production resilience

    Attributes:
        adapter_key: The key identifier for this adapter type ("async_redis")
        obj_key: Legacy key identifier (for backward compatibility)

    Configuration Parameters:
        Connection (choose one):
        - url: Redis connection string (e.g., "redis://localhost:6379/0")
        - host: Redis host (default: "localhost")
        - port: Redis port (default: 6379)
        - db: Redis database number (default: 0)
        - username: Redis username (Redis 6+)
        - password: Redis password

        Connection Pool:
        - max_connections: Pool size (default: 20)
        - health_check_interval: Health check seconds (default: 30)
        - socket_timeout: Socket timeout (default: 5.0)
        - socket_connect_timeout: Connect timeout (default: 5.0)

        Read Operations:
        - key: Specific key to retrieve (from_obj)
        - pattern: Key pattern for scanning (e.g., "user:*")
        - scan_count: SCAN batch size (default: 100)

        Write Operations:
        - key_field: Model field to use as Redis key (default: "id")
        - key_prefix: Prefix for all keys (default: "")
        - key_template: Template with placeholders (e.g., "user:{id}")
        - ttl: TTL in seconds
        - nx: SET IF NOT EXISTS (default: False)
        - xx: SET IF EXISTS (default: False)

        Serialization:
        - serialization: "msgpack" (default) or "json"

    Example:
        ```python
        import asyncio
        from pydantic import BaseModel
        from pydapter.extras.async_redis_ import AsyncRedisAdapter

        class User(BaseModel):
            id: int
            name: str
            email: str

        async def main():
            # Store single user
            user = User(id=1, name="John", email="john@example.com")
            write_config = {
                "url": "redis://localhost:6379/0",
                "key_template": "user:{id}",
                "ttl": 3600
            }
            await AsyncRedisAdapter.to_obj(user, **write_config)

            # Retrieve single user
            read_config = {
                "url": "redis://localhost:6379/0",
                "key": "user:1"
            }
            retrieved_user = await AsyncRedisAdapter.from_obj(User, read_config)

            # Store multiple users
            users = [
                User(id=2, name="Jane", email="jane@example.com"),
                User(id=3, name="Bob", email="bob@example.com")
            ]
            await AsyncRedisAdapter.to_obj(users, many=True, **write_config)

            # Retrieve multiple users by pattern
            bulk_config = {
                "url": "redis://localhost:6379/0",
                "pattern": "user:*"
            }
            all_users = await AsyncRedisAdapter.from_obj(User, bulk_config, many=True)

        asyncio.run(main())
        ```
    """

    adapter_key: ClassVar[str] = "async_redis"
    obj_key: ClassVar[str] = "async_redis"  # Backward compatibility

    @classmethod
    def _validate_config(cls, config: dict[str, Any], operation: str) -> dict[str, Any]:
        """Validate and normalize configuration parameters."""
        if not isinstance(config, dict):
            raise AdapterValidationError(
                f"Configuration must be a dictionary for {operation}",
                adapter="async_redis",
                operation=operation,
            )

        # Ensure we have connection info
        if not any(k in config for k in ("url", "host")):
            # Default to localhost
            config = dict(config)  # Don't modify original
            config["host"] = config.get("host", "localhost")
            config["port"] = config.get("port", 6379)
            config["db"] = config.get("db", 0)

        return config

    @classmethod
    def _get_connection_url(cls, config: dict[str, Any]) -> str:
        """Extract or build Redis connection URL from configuration."""
        if "url" in config:
            return config["url"]

        # Build URL from components
        host = config.get("host", "localhost")
        port = config.get("port", 6379)
        db = config.get("db", 0)
        username = config.get("username")
        password = config.get("password")

        if username and password:
            return f"redis://{username}:{password}@{host}:{port}/{db}"
        elif password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"

    @classmethod
    async def _create_client(cls, config: dict[str, Any]) -> AsyncRedis:
        """Create optimized Redis client with connection pooling."""
        try:
            url = cls._get_connection_url(config)

            # Connection pool configuration
            pool = redis.ConnectionPool.from_url(
                url,
                max_connections=config.get("max_connections", 20),
                decode_responses=False,  # Handle bytes for msgpack
                health_check_interval=config.get("health_check_interval", 30),
                socket_timeout=config.get("socket_timeout", 5.0),
                socket_connect_timeout=config.get("socket_connect_timeout", 5.0),
            )

            client = AsyncRedis(connection_pool=pool)

            # Validate connection
            await client.ping()
            return client

        except redis.ConnectionError as e:
            raise ConnectionError(
                f"Failed to create Redis client: {e}",
                adapter="async_redis",
                url=url if "url" in locals() else "unknown",
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Unexpected error creating Redis client: {e}",
                adapter="async_redis",
            ) from e

    @classmethod
    def _get_retry_config(cls, max_attempts: int = 3) -> dict[str, Any]:
        """Get tenacity retry configuration for Redis operations."""
        return {
            "retry": retry_if_exception_type(
                (
                    redis.ConnectionError,
                    redis.TimeoutError,
                    redis.RedisError,
                    ConnectionRefusedError,
                    TimeoutError,
                )
            ),
            "stop": stop_after_attempt(max_attempts),
            "wait": wait_exponential(multiplier=0.1, max=60.0),
        }

    @classmethod
    async def _execute_with_retry(cls, operation, operation_name: str = "redis_operation"):
        """Execute Redis operation with comprehensive retry logic."""
        try:
            retry_config = cls._get_retry_config()
            async for attempt in AsyncRetrying(**retry_config):
                with attempt:
                    return await operation()
        except redis.ConnectionError as e:
            raise ConnectionError(
                f"Redis connection failed during {operation_name}: {e}",
                adapter="async_redis",
                operation=operation_name,
            ) from e
        except redis.TimeoutError as e:
            raise ConnectionError(
                f"Redis timeout during {operation_name}: {e}",
                adapter="async_redis",
                operation=operation_name,
            ) from e
        except redis.RedisError as e:
            raise QueryError(
                f"Redis operation '{operation_name}' failed: {e}",
                adapter="async_redis",
                operation=operation_name,
            ) from e
        except Exception as e:
            raise QueryError(
                f"Unexpected error during Redis {operation_name}: {e}",
                adapter="async_redis",
                operation=operation_name,
            ) from e

    @classmethod
    def _serialize_model(
        cls,
        model: BaseModel,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        serialization: str = "msgpack",
    ) -> bytes:
        """Serialize Pydantic model to bytes using dispatch_adapt_meth."""
        try:
            # Use dispatch_adapt_meth for flexible method calling
            data = dispatch_adapt_meth(adapt_meth, model, adapt_kw or {}, type(model))

            if serialization == "msgpack":
                return ormsgpack.packb(data)
            elif serialization == "json":
                return orjson.dumps(data)
            else:
                raise AdapterValidationError(
                    f"Unsupported serialization format: {serialization}",
                    adapter="async_redis",
                    serialization=serialization,
                )
        except AdapterValidationError:
            raise
        except Exception as e:
            cls._handle_error(
                e,
                "validation",
                model_type=type(model).__name__,
                serialization=serialization,
            )

    @classmethod
    def _deserialize_model(
        cls,
        data: bytes,
        model_class: type[T],
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        serialization: str = "msgpack",
        validation_errors: tuple[type[Exception], ...] = (PydanticValidationError,),
    ) -> T:
        """Deserialize bytes to Pydantic model using dispatch_adapt_meth."""
        try:
            if serialization == "msgpack":
                parsed_data = ormsgpack.unpackb(data)
            elif serialization == "json":
                parsed_data = orjson.loads(data)
            else:
                raise AdapterValidationError(
                    f"Unsupported serialization format: {serialization}",
                    adapter="async_redis",
                    serialization=serialization,
                )

            # Use dispatch_adapt_meth for flexible method calling
            return dispatch_adapt_meth(adapt_meth, parsed_data, adapt_kw or {}, model_class)

        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=parsed_data if "parsed_data" in locals() else None,
                errors=e.errors() if hasattr(e, "errors") else None,
                model_type=model_class.__name__,
            )
        except AdapterValidationError:
            raise
        except Exception as e:
            cls._handle_error(
                e,
                "validation",
                model_type=model_class.__name__,
                serialization=serialization,
            )

    @classmethod
    def _generate_key(cls, model: BaseModel | dict, config: dict[str, Any]) -> str:
        """Generate Redis key for a model based on configuration."""
        key_prefix = config.get("key_prefix", "")
        key_template = config.get("key_template")
        key_field = config.get("key_field", "id")

        # Get model data as dict (handle both BaseModel and dict inputs)
        if hasattr(model, "model_dump"):
            # It's a Pydantic model
            model_dict = model.model_dump()
        elif isinstance(model, dict):
            # It's already a dict
            model_dict = model
        else:
            raise AdapterValidationError(
                f"Invalid model type for key generation: {type(model)}",
                adapter="async_redis",
                model_type=type(model).__name__,
            )

        if key_template:
            # Use template with model fields
            try:
                key = key_template.format(**model_dict)
            except KeyError as e:
                raise AdapterValidationError(
                    f"Key template references missing field: {e}",
                    adapter="async_redis",
                    template=key_template,
                    available_fields=list(model_dict.keys()),
                ) from e
        else:
            # Use key_field
            try:
                key_value = model_dict[key_field]
                key = f"{key_prefix}{key_value}" if key_prefix else str(key_value)
            except KeyError:
                raise AdapterValidationError(
                    f"Model missing required key field: {key_field}",
                    adapter="async_redis",
                    key_field=key_field,
                    available_fields=list(model_dict.keys()),
                )

        return key

    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (PydanticValidationError,),
        **kw,
    ) -> T | list[T]:
        """
        Retrieve Pydantic models from Redis.

        Args:
            subj_cls: The Pydantic model class to deserialize to
            obj: Configuration dictionary containing Redis connection and read parameters
            many: Whether to retrieve multiple models (pattern-based scan)
            adapt_meth: Pydantic method to use for validation (default: "model_validate")
            adapt_kw: Keyword arguments for adaptation method
            validation_errors: Tuple of expected validation error types
            **kw: Additional keyword arguments

        Returns:
            Single model instance or list of model instances

        Raises:
            ConnectionError: Redis connection issues
            QueryError: Redis operation failures
            ValidationError: Invalid configuration or model validation errors
            ResourceError: Key not found (when not using patterns)
        """
        try:
            config = cls._validate_config(obj, "read")
            serialization = config.get("serialization", "msgpack")
            adapt_kw = adapt_kw or {}

            client = await cls._create_client(config)

            try:
                if many:
                    # Pattern-based retrieval
                    pattern = config.get("pattern", "*")
                    scan_count = config.get("scan_count", 100)

                    async def scan_operation():
                        keys = []
                        async for key in client.scan_iter(match=pattern, count=scan_count):
                            keys.append(key)
                        return keys

                    keys = await cls._execute_with_retry(scan_operation, "scan_keys")

                    if not keys:
                        return []

                    # Retrieve all values
                    async def mget_operation():
                        return await client.mget(keys)

                    values = await cls._execute_with_retry(mget_operation, "mget_values")

                    # Deserialize all models
                    models = []
                    for value in values:
                        if value is not None:
                            model = cls._deserialize_model(
                                value,
                                subj_cls,
                                adapt_meth,
                                adapt_kw,
                                serialization,
                                validation_errors,
                            )
                            models.append(model)

                    return models

                else:
                    # Single key retrieval
                    key = config.get("key")
                    if not key:
                        raise AdapterValidationError(
                            "Missing 'key' parameter for single object retrieval",
                            adapter="async_redis",
                            operation="read",
                        )

                    async def get_operation():
                        return await client.get(key)

                    value = await cls._execute_with_retry(get_operation, "get_value")

                    if value is None:
                        raise ResourceError(
                            f"Key not found in Redis: {key}",
                            adapter="async_redis",
                            resource=key,
                        )

                    return cls._deserialize_model(
                        value, subj_cls, adapt_meth, adapt_kw, serialization, validation_errors
                    )

            finally:
                await client.aclose()

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)

    @classmethod
    async def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> Any:
        """
        Store Pydantic models to Redis.

        Args:
            subj: Single model instance or list of model instances
            many: Whether storing multiple models
            adapt_meth: Pydantic method to use for dumping (default: "model_dump")
            adapt_kw: Keyword arguments for adaptation method
            **kw: Configuration dictionary containing Redis connection and write parameters

        Returns:
            Operation result (number of keys set or similar)

        Raises:
            ConnectionError: Redis connection issues
            QueryError: Redis operation failures
            ValidationError: Invalid configuration or serialization errors
        """
        try:
            config = cls._validate_config(kw, "write")
            serialization = config.get("serialization", "msgpack")
            adapt_kw = adapt_kw or {}
            ttl = config.get("ttl")
            nx = config.get("nx", False)
            xx = config.get("xx", False)

            client = await cls._create_client(config)

            try:
                if many:
                    # Bulk operations
                    models = subj if isinstance(subj, list) else [subj]
                    pipeline_size = config.get("pipeline_size", 100)

                    # Process in batches for large datasets
                    total_set = 0
                    for i in range(0, len(models), pipeline_size):
                        batch = models[i : i + pipeline_size]

                        async def pipeline_operation():
                            pipe = client.pipeline()
                            for model in batch:
                                key = cls._generate_key(model, config)
                                value = cls._serialize_model(
                                    model, adapt_meth, adapt_kw, serialization
                                )

                                if ttl and nx:
                                    pipe.set(key, value, ex=ttl, nx=True)
                                elif ttl and xx:
                                    pipe.set(key, value, ex=ttl, xx=True)
                                elif ttl:
                                    pipe.setex(key, ttl, value)
                                elif nx:
                                    pipe.set(key, value, nx=True)
                                elif xx:
                                    pipe.set(key, value, xx=True)
                                else:
                                    pipe.set(key, value)

                            return await pipe.execute()

                        results = await cls._execute_with_retry(pipeline_operation, "pipeline_set")
                        total_set += sum(1 for r in results if r)

                    return total_set

                else:
                    # Single model operation
                    model = subj
                    # Use explicit key if provided, otherwise generate one
                    key = config.get("key") or cls._generate_key(model, config)
                    value = cls._serialize_model(model, adapt_meth, adapt_kw, serialization)

                    async def set_operation():
                        if ttl and nx:
                            return await client.set(key, value, ex=ttl, nx=True)
                        elif ttl and xx:
                            return await client.set(key, value, ex=ttl, xx=True)
                        elif ttl:
                            return await client.setex(key, ttl, value)
                        elif nx:
                            return await client.set(key, value, nx=True)
                        elif xx:
                            return await client.set(key, value, xx=True)
                        else:
                            return await client.set(key, value)

                    result = await cls._execute_with_retry(set_operation, "set_value")
                    return 1 if result else 0

            finally:
                await client.aclose()

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)
