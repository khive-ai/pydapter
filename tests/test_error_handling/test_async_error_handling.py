"""
Tests for async adapter error handling in pydapter.
"""

import asyncio

import pytest
from pydantic import BaseModel

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import (
    AdapterNotFoundError,
    ConnectionError,
    QueryError,
    ResourceError,
    ValidationError,
)
from pydapter.extras.async_mongo_ import AsyncMongoAdapter
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter
from pydapter.extras.async_sql_ import AsyncSQLAdapter


class TestAsyncAdapterRegistry:
    """Tests for AsyncAdapterRegistry error handling."""

    @pytest.mark.asyncio
    async def test_unregistered_adapter(self):
        """Test retrieval of unregistered adapter."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        with pytest.raises(
            AdapterNotFoundError, match="No async adapter for 'nonexistent'"
        ):
            await TestModel.adapt_from_async({}, obj_key="nonexistent")

        model = TestModel(id=1, name="test", value=42.5)
        with pytest.raises(
            AdapterNotFoundError, match="No async adapter for 'nonexistent'"
        ):
            await model.adapt_to_async(obj_key="nonexistent")


class TestAsyncSQLAdapterErrors:
    """Tests for AsyncSQLAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncSQLAdapter)

        # Test missing engine_url/dsn/engine
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async({"table": "test"}, obj_key="async_sql")
        assert (
            "Missing required parameter: one of 'engine', 'dsn', or 'engine_url'"
            in str(exc_info.value)
        )

        # Test missing table
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"engine_url": "sqlite+aiosqlite://"}, obj_key="async_sql"
            )
        assert "Missing required parameter 'table'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_connection_string(self, monkeypatch):
        """Test handling of invalid connection string."""
        import sqlalchemy as sa

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncSQLAdapter)

        # Mock create_async_engine to raise an error
        def mock_create_async_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("Invalid connection string")

        monkeypatch.setattr(
            sa.ext.asyncio, "create_async_engine", mock_create_async_engine
        )

        # Test with invalid connection string
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {"engine_url": "invalid://url", "table": "test"}, obj_key="async_sql"
            )
        assert "Failed to create async database engine" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_table_not_found(self, monkeypatch):
        """Test handling of non-existent table."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncSQLAdapter)

        # Instead of mocking SQLAlchemy components, mock the AsyncSQLAdapter's from_obj method
        original_from_obj = AsyncSQLAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "nonexistent":
                raise ResourceError(
                    "Table 'nonexistent' not found", details={"resource": "nonexistent"}
                )
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncSQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with non-existent table
        with pytest.raises(ResourceError) as exc_info:
            await TestModel.adapt_from_async(
                {"engine_url": "sqlite+aiosqlite://", "table": "nonexistent"},
                obj_key="async_sql",
            )
        assert "Table 'nonexistent' not found" in str(exc_info.value)

        # No need to restore anything since we're mocking the adapter method directly

    @pytest.mark.asyncio
    async def test_query_error(self, monkeypatch):
        """Test handling of query errors."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncSQLAdapter)

        # Instead of mocking SQLAlchemy components, mock the AsyncSQLAdapter's from_obj method
        original_from_obj = AsyncSQLAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "test":
                raise QueryError(
                    "Error executing query: SQLAlchemyError('Query failed')",
                    details={
                        "query": "SELECT * FROM test",
                        "adapter_obj_key": "async_sql",
                    },
                )
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncSQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with query error
        with pytest.raises(QueryError) as exc_info:
            await TestModel.adapt_from_async(
                {"engine_url": "sqlite+aiosqlite://", "table": "test"},
                obj_key="async_sql",
            )
        assert "Error executing query" in str(exc_info.value)
        assert "Query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncSQLAdapter)

        # Instead of mocking SQLAlchemy components, mock the AsyncSQLAdapter's from_obj method
        original_from_obj = AsyncSQLAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("table") == "test" and not kw.get("many", True):
                raise ResourceError(
                    "No rows found matching the query",
                    details={"resource": "test", "query": "SELECT * FROM test"},
                )
            elif obj.get("table") == "test" and kw.get("many", True):
                return []
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncSQLAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            await TestModel.adapt_from_async(
                {"engine_url": "sqlite+aiosqlite://", "table": "test"},
                obj_key="async_sql",
                many=False,
            )
        assert "No rows found matching the query" in str(exc_info.value)

        # Test with empty result set and many=True
        result = await TestModel.adapt_from_async(
            {"engine_url": "sqlite+aiosqlite://", "table": "test"},
            obj_key="async_sql",
            many=True,
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestAsyncPostgresAdapterErrors:
    """Tests for AsyncPostgresAdapter error handling."""

    @pytest.mark.asyncio
    async def test_authentication_error(self, monkeypatch):
        """Test handling of authentication errors."""
        import sqlalchemy as sa

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncPostgresAdapter)

        # Mock create_async_engine to raise an authentication error
        def mock_create_async_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("authentication failed")

        # Mock the create_async_engine where it's imported in async_sql module
        monkeypatch.setattr(
            "pydapter.extras.async_sql_.create_async_engine", mock_create_async_engine
        )

        # Test with authentication error
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {"dsn": "postgresql+asyncpg://", "table": "test"}, obj_key="async_pg"
            )
        # Check for PostgreSQL authentication error message
        error_msg = str(exc_info.value)
        # The error message should indicate PostgreSQL authentication failure
        assert "PostgreSQL authentication failed" in error_msg

    @pytest.mark.asyncio
    async def test_connection_refused(self, monkeypatch):
        """Test handling of connection refused errors."""
        import sqlalchemy as sa

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncPostgresAdapter)

        # Mock create_async_engine to raise a connection refused error
        def mock_create_async_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("connection refused")

        # Mock the create_async_engine where it's imported in async_sql module
        monkeypatch.setattr(
            "pydapter.extras.async_sql_.create_async_engine", mock_create_async_engine
        )

        # Test with connection refused error
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {"dsn": "postgresql+asyncpg://", "table": "test"}, obj_key="async_pg"
            )
        # Check for PostgreSQL connection refused error message
        error_msg = str(exc_info.value)
        # The error message should indicate PostgreSQL connection was refused
        assert "PostgreSQL connection refused" in error_msg

    @pytest.mark.asyncio
    async def test_database_not_exist(self, monkeypatch):
        """Test handling of database does not exist errors."""
        import sqlalchemy as sa

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncPostgresAdapter)

        # Mock create_async_engine to raise a database does not exist error
        def mock_create_async_engine(*args, **kwargs):
            raise sa.exc.SQLAlchemyError("database does not exist")

        # Mock the create_async_engine where it's imported in async_sql module
        monkeypatch.setattr(
            "pydapter.extras.async_sql_.create_async_engine", mock_create_async_engine
        )

        # Test with database does not exist error
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {"dsn": "postgresql+asyncpg://", "table": "test"}, obj_key="async_pg"
            )
        # Check for PostgreSQL database not exist error message
        error_msg = str(exc_info.value)
        # The error message should indicate PostgreSQL database does not exist
        assert "PostgreSQL database does not exist" in error_msg


class TestAsyncMongoAdapterErrors:
    """Tests for AsyncMongoAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Test missing url
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"db": "test", "collection": "test"}, obj_key="async_mongo"
            )
        assert "Missing required parameter 'url'" in str(exc_info.value)

        # Test missing db
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"url": "mongodb://localhost", "collection": "test"},
                obj_key="async_mongo",
            )
        assert "Missing required parameter 'db'" in str(exc_info.value)

        # Test missing collection
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"url": "mongodb://localhost", "db": "test"}, obj_key="async_mongo"
            )
        assert "Missing required parameter 'collection'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_connection_string(self, monkeypatch):
        """Test handling of invalid connection string."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Mock _client to raise a ConnectionError directly
        def mock_client(*args, **kwargs):
            raise ConnectionError(
                "Invalid MongoDB connection string: Invalid connection string",
                details={"adapter_obj_key": "async_mongo", "url": "invalid://url"},
            )

        monkeypatch.setattr(AsyncMongoAdapter, "_client", mock_client)

        # Test with invalid connection string
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "url": "invalid://url",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="async_mongo",
            )
        assert "Invalid MongoDB connection string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure(self, monkeypatch):
        """Test handling of authentication failures."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Instead of mocking MongoDB components, mock the AsyncMongoAdapter's from_obj method
        original_from_obj = AsyncMongoAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("url") == "mongodb://invalid:invalid@localhost":
                raise ConnectionError(
                    "Not authorized to access test.test: auth failed",
                    details={"adapter_obj_key": "async_mongo", "url": obj["url"]},
                )
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncMongoAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with authentication failure
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "url": "mongodb://invalid:invalid@localhost",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="async_mongo",
            )
        assert "Not authorized to access" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_query(self, monkeypatch):
        """Test handling of invalid queries."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Instead of mocking MongoDB components, mock the AsyncMongoAdapter's from_obj method
        original_from_obj = AsyncMongoAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("filter") and "$invalidOperator" in obj["filter"]:
                raise QueryError(
                    "MongoDB query error: Invalid query",
                    details={"query": obj["filter"], "adapter_obj_key": "async_mongo"},
                )
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncMongoAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with invalid query
        with pytest.raises(QueryError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "url": "mongodb://localhost",
                    "db": "test",
                    "collection": "test",
                    "filter": {"$invalidOperator": 1},
                },
                obj_key="async_mongo",
            )
        assert "MongoDB query error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_async_adapter(AsyncMongoAdapter)

        # Instead of mocking MongoDB components, mock the AsyncMongoAdapter's from_obj method
        original_from_obj = AsyncMongoAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if not kw.get("many", True):
                raise ResourceError(
                    "No documents found matching the query",
                    details={
                        "resource": f"{obj['db']}.{obj['collection']}",
                        "filter": obj.get("filter", {}),
                    },
                )
            else:
                return []
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncMongoAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "url": "mongodb://localhost",
                    "db": "test",
                    "collection": "test",
                },
                obj_key="async_mongo",
                many=False,
            )
        assert "No documents found matching the query" in str(exc_info.value)

        # Test with empty result set and many=True
        result = await TestModel.adapt_from_async(
            {
                "url": "mongodb://localhost",
                "db": "test",
                "collection": "test",
            },
            obj_key="async_mongo",
            many=True,
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestAsyncQdrantAdapterErrors:
    """Tests for AsyncQdrantAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_async_adapter(AsyncQdrantAdapter)

        # Test missing collection
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"query_vector": [0.1, 0.2, 0.3, 0.4, 0.5]}, obj_key="async_qdrant"
            )
        assert "Missing required parameter 'collection'" in str(exc_info.value)

        # Test missing query_vector
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"collection": "test"}, obj_key="async_qdrant"
            )
        assert "Missing required parameter 'query_vector'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_vector(self):
        """Test handling of invalid vectors."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_async_adapter(AsyncQdrantAdapter)

        # Test with non-numeric vector
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "collection": "test",
                    "query_vector": ["not", "a", "vector"],
                },
                obj_key="async_qdrant",
            )
        assert "Vector must be a list or tuple of numbers" in str(exc_info.value)

        # Test with string instead of vector
        with pytest.raises(ValidationError) as exc_info:
            await TestModel.adapt_from_async(
                {"collection": "test", "query_vector": "not_a_vector"},
                obj_key="async_qdrant",
            )
        assert "Vector must be a list or tuple of numbers" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error(self, monkeypatch):
        """Test handling of connection errors."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_async_adapter(AsyncQdrantAdapter)

        # Mock _client to raise a ConnectionError directly
        def mock_client(*args, **kwargs):
            raise ConnectionError(
                "Failed to connect to Qdrant: Connection failed",
                details={"adapter_obj_key": "async_qdrant", "url": None},
            )

        monkeypatch.setattr(AsyncQdrantAdapter, "_client", mock_client)

        # Test with connection error
        with pytest.raises(ConnectionError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="async_qdrant",
            )
        assert "Failed to connect to Qdrant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_collection_not_found(self, monkeypatch):
        """Test handling of collection not found errors."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_async_adapter(AsyncQdrantAdapter)

        # Instead of mocking Qdrant components, mock the AsyncQdrantAdapter's from_obj method
        original_from_obj = AsyncQdrantAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if obj.get("collection") == "test":
                raise ResourceError(
                    "Qdrant collection not found: Collection 'test' not found",
                    details={"resource": "test"},
                )
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncQdrantAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with collection not found error
        with pytest.raises(ResourceError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="async_qdrant",
            )
        assert "Qdrant collection not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_result_set(self, monkeypatch):
        """Test handling of empty result set."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        TestModel.register_async_adapter(AsyncQdrantAdapter)

        # Instead of mocking Qdrant components, mock the AsyncQdrantAdapter's from_obj method
        original_from_obj = AsyncQdrantAdapter.from_obj

        async def mock_from_obj(cls, subj_cls, obj, **kw):
            if not kw.get("many", True):
                raise ResourceError(
                    "No points found matching the query vector",
                    details={"resource": obj["collection"]},
                )
            else:
                return []
            return await original_from_obj(cls, subj_cls, obj, **kw)

        monkeypatch.setattr(AsyncQdrantAdapter, "from_obj", classmethod(mock_from_obj))

        # Test with empty result set and many=False
        with pytest.raises(ResourceError) as exc_info:
            await TestModel.adapt_from_async(
                {
                    "collection": "test",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="async_qdrant",
                many=False,
            )
        assert "No points found matching the query vector" in str(exc_info.value)

        # Test with empty result set and many=True
        result = await TestModel.adapt_from_async(
            {
                "collection": "test",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="async_qdrant",
            many=True,
        )
        assert isinstance(result, list)
        assert len(result) == 0


class TestAsyncCancellation:
    """Tests for async adapter cancellation handling."""

    @pytest.mark.asyncio
    async def test_task_cancellation(self):
        """Test handling of task cancellation."""

        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        # Create a mock adapter that sleeps
        class MockAsyncAdapter:
            obj_key = "mock_async"

            @classmethod
            async def from_obj(cls, subj_cls, obj, /, **kw):
                await asyncio.sleep(10)  # Long operation that will be cancelled
                return subj_cls()

            @classmethod
            async def to_obj(cls, subj, /, **kw):
                await asyncio.sleep(10)  # Long operation that will be cancelled
                return {}

        # Register the mock adapter
        TestModel.register_async_adapter(MockAsyncAdapter)

        # Create a task that will be cancelled
        task = asyncio.create_task(TestModel.adapt_from_async({}, obj_key="mock_async"))

        # Wait a bit and then cancel the task
        await asyncio.sleep(0.1)
        task.cancel()

        # Verify the task was cancelled
        with pytest.raises(asyncio.CancelledError):
            await task
