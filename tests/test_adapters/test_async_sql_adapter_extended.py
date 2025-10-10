"""
Extended tests for Async SQL adapter functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel
import pytest

from pydapter.core import Adaptable
from pydapter.extras.async_sql_ import AsyncSQLAdapter


class AsyncContextManagerMock:
    """A mock for async context managers."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_sql_model_factory():
    """Factory for creating test models with Async SQL adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Async SQL adapter
        TestModel.register_adapter(AsyncSQLAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def async_sql_sample(async_sql_model_factory):
    """Create a sample model instance."""
    return async_sql_model_factory(id=1, name="test", value=42.5)


class TestAsyncSQLAdapterExtended:
    """Extended tests for Async SQL adapter functionality."""

    def test_async_sql_table_helper(self):
        """Test the _table helper method."""
        # Create mock metadata and bind
        mock_metadata = MagicMock()
        mock_table = MagicMock()

        # Mock the sa.Table function
        with patch("pydapter.extras.async_sql_.sa.Table", return_value=mock_table) as mock_sa_table:
            # Call the _table helper
            result = AsyncSQLAdapter._table(mock_metadata, "test_table")

            # Verify the result
            assert result == mock_table

            # Verify sa.Table was called with correct arguments
            # Note: For async operations, we don't use autoload_with
            mock_sa_table.assert_called_once_with("test_table", mock_metadata)

    @pytest.mark.asyncio
    async def test_async_sql_from_obj_with_selectors(self):
        """Test conversion from Async SQL record to model with selectors."""
        # Setup mocks
        with patch("pydapter.extras.async_sql_.create_async_engine") as mock_create_engine:
            # Create a mock connection that supports run_sync
            mock_conn = AsyncMock()

            # Mock run_sync to return our test data
            async def mock_run_sync(func):
                # Simulate what our sync function would return
                return [{"id": 1, "name": "test", "value": 42.5}]

            mock_conn.run_sync = mock_run_sync

            # Create a mock engine with a begin method that returns our async context manager
            mock_engine = MagicMock()
            mock_begin_ctx = AsyncContextManagerMock(mock_conn)
            mock_engine.begin = MagicMock(return_value=mock_begin_ctx)
            mock_create_engine.return_value = mock_engine

            # Create a test model class
            class TestModel(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            # Register the adapter
            TestModel.register_adapter(AsyncSQLAdapter)

            # Directly test the adapter's from_obj method
            result = await AsyncSQLAdapter.from_obj(
                TestModel,
                {
                    "engine_url": "sqlite+aiosqlite:///:memory:",
                    "table": "test_table",
                    "selectors": {"id": 1},
                },
            )

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            assert result[0].name == "test"
            assert result[0].value == 42.5

    @pytest.mark.asyncio
    async def test_async_sql_from_obj_single(self):
        """Test conversion from Async SQL record to model with many=False."""
        # Setup mocks
        with patch("pydapter.extras.async_sql_.create_async_engine") as mock_create_engine:
            # Create a mock connection that supports run_sync
            mock_conn = AsyncMock()

            # Mock run_sync to return our test data
            async def mock_run_sync(func):
                # Simulate what our sync function would return
                return [{"id": 1, "name": "test", "value": 42.5}]

            mock_conn.run_sync = mock_run_sync

            # Create a mock engine with a begin method that returns our async context manager
            mock_engine = MagicMock()
            mock_begin_ctx = AsyncContextManagerMock(mock_conn)
            mock_engine.begin = MagicMock(return_value=mock_begin_ctx)
            mock_create_engine.return_value = mock_engine

            # Create a test model class
            class TestModel(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            # Register the adapter
            TestModel.register_adapter(AsyncSQLAdapter)

            # Directly test the adapter's from_obj method with many=False
            result = await AsyncSQLAdapter.from_obj(
                TestModel,
                {
                    "engine_url": "sqlite+aiosqlite:///:memory:",
                    "table": "test_table",
                },
                many=False,
            )

            # Verify the result is a single model, not a list
            assert not isinstance(result, list)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5

    @pytest.mark.asyncio
    async def test_async_sql_to_obj_multiple_items(self):
        """Test conversion from multiple models to Async SQL records."""

        # Create test models
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        model1 = TestModel(id=1, name="test1", value=42.5)
        model2 = TestModel(id=2, name="test2", value=43.5)
        models = [model1, model2]

        # Setup mocks
        with patch("pydapter.extras.async_sql_.create_async_engine") as mock_create_engine:
            # Create a mock connection that supports run_sync
            mock_conn = AsyncMock()

            # Mock run_sync to simulate successful insert
            async def mock_run_sync(func):
                # Simulate what our sync function would return (rowcount)
                return 2

            mock_conn.run_sync = mock_run_sync

            # Create a mock engine with a begin method that returns our async context manager
            mock_engine = MagicMock()
            mock_begin_ctx = AsyncContextManagerMock(mock_conn)
            mock_engine.begin = MagicMock(return_value=mock_begin_ctx)
            mock_create_engine.return_value = mock_engine

            # Register the adapter
            TestModel.register_adapter(AsyncSQLAdapter)

            # Directly test the adapter's to_obj method with multiple items
            result = await AsyncSQLAdapter.to_obj(
                models,
                engine_url="sqlite+aiosqlite:///:memory:",
                table="test_table",
            )

            # Verify the result
            assert result == {"inserted_count": 2}

    @pytest.mark.asyncio
    async def test_async_sql_to_obj_with_single_item(self, async_sql_sample):
        """Test conversion from a single model to Async SQL record."""
        # Setup mocks
        with patch("pydapter.extras.async_sql_.create_async_engine") as mock_create_engine:
            # Create a mock connection that supports run_sync
            mock_conn = AsyncMock()

            # Mock run_sync to simulate successful insert
            async def mock_run_sync(func):
                # Simulate what our sync function would return (rowcount)
                return 1

            mock_conn.run_sync = mock_run_sync

            # Create a mock engine with a begin method that returns our async context manager
            mock_engine = MagicMock()
            mock_begin_ctx = AsyncContextManagerMock(mock_conn)
            mock_engine.begin = MagicMock(return_value=mock_begin_ctx)
            mock_create_engine.return_value = mock_engine

            # Test to_obj with a single item
            result = await async_sql_sample.adapt_to(
                obj_key="async_sql",
                engine_url="sqlite+aiosqlite:///:memory:",
                table="test_table",
            )

            # Verify the result
            assert result == {"inserted_count": 1}
