"""
Integration tests for AsyncNeo4jAdapter.

These tests use mocked Neo4j connections to simulate database interactions.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import ConnectionError, ResourceError, QueryError
from pydapter.extras.async_neo4j_ import AsyncNeo4jAdapter


class AsyncTestModel(BaseModel, AsyncAdaptable):
    """Test model for integration tests."""
    id: int
    name: str
    value: float


# Register the adapter with the model class
AsyncTestModel.register_async_adapter(AsyncNeo4jAdapter)


@pytest.fixture(scope="session")
def async_model_factory():
    """Factory for creating test models."""
    return lambda **kwargs: AsyncTestModel(**kwargs)


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for integration tests."""
    mock_driver = AsyncMock()
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    
    # Configure mocks for async context managers
    mock_driver.session = MagicMock(return_value=mock_session)
    
    # Configure the run method to return a mock result
    run_future = asyncio.Future()
    run_future.set_result(mock_result)
    mock_session.run.return_value = run_future
    
    # Set up the async iterator for result
    mock_record = MagicMock()
    mock_record.__getitem__.return_value = MagicMock(_properties={"id": 44, "name": "test_async_neo4j", "value": 90.12})
    
    async def mock_aiter():
        yield mock_record
        
    mock_result.__aiter__.return_value = mock_aiter()
    
    # Mock session.close to return a completed future
    close_future = asyncio.Future()
    close_future.set_result(None)
    mock_session.close.return_value = close_future
    
    # Ensure the session is properly awaited
    mock_session.__await__ = lambda: iter([mock_session])
    
    # Patch the AsyncGraphDatabase.driver method
    with patch('neo4j.AsyncGraphDatabase.driver', return_value=mock_driver):
        # Patch the AsyncNeo4jAdapter._create_driver method
        with patch('pydapter.extras.async_neo4j_.AsyncNeo4jAdapter._create_driver', return_value=mock_driver):
            return mock_driver, mock_session, mock_result


class TestAsyncNeo4jIntegration:
    """Integration tests for AsyncNeo4jAdapter."""
    
    @pytest.mark.asyncio
    async def test_async_neo4j_single_node(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test creating and retrieving a single node."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        
        # Create test instance
        test_model = async_model_factory(id=44, name="test_async_neo4j", value=90.12)
        
        # Save to Neo4j
        result = await test_model.adapt_to_async(
            obj_key="async_neo4j",
            url="bolt://localhost:7687",
            auth=("neo4j", "password"),
            label="AsyncTestModel",
        )
        
        assert result["merged_count"] == 1
        
        # Verify the query was constructed correctly
        mock_session.run.assert_called_with(
            "MERGE (n:`AsyncTestModel` {id: $val}) SET n += $props",
            val=44,
            props={"id": 44, "name": "test_async_neo4j", "value": 90.12}
        )
        
        # Retrieve from Neo4j
        retrieved = await AsyncTestModel.adapt_from_async(
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "AsyncTestModel",
                "where": "n.id = 44",
            },
            obj_key="async_neo4j",
            many=False,
        )
        
        # Verify retrieved model
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value
    
    @pytest.mark.asyncio
    async def test_async_neo4j_batch_operations(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test batch operations with multiple nodes."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        
        # Create test instances
        model_cls = async_model_factory(id=1, name="test1", value=1.1).__class__
        models = [
            async_model_factory(id=i, name=f"batch_{i}", value=float(i * 1.5))
            for i in range(1, 6)
        ]
        
        # Mock multiple records for batch retrieval
        mock_records = []
        for i in range(1, 6):
            mock_record = MagicMock()
            mock_record.__getitem__.return_value = MagicMock(
                _properties={"id": i, "name": f"batch_{i}", "value": float(i * 1.5)}
            )
            mock_records.append(mock_record)
        
        # Update the mock_aiter function to yield multiple records
        async def mock_batch_aiter():
            for record in mock_records:
                yield record
        
        # Save all models to Neo4j
        for model in models:
            result = await model.adapt_to_async(
                obj_key="async_neo4j",
                url="bolt://localhost:7687",
                auth=("neo4j", "password"),
                label="BatchTest",
            )
            assert result["merged_count"] == 1
        
        # Set up the batch retrieval
        mock_result.__aiter__.return_value = mock_batch_aiter()
        
        # Retrieve all models from Neo4j
        retrieved = await model_cls.adapt_from_async(
            {"url": "bolt://localhost:7687", "auth": ("neo4j", "password"), "label": "BatchTest"},
            obj_key="async_neo4j",
            many=True,
        )
        
        # Verify retrieved models
        assert len(retrieved) == 5
        
        # Sort by ID for comparison
        retrieved.sort(key=lambda x: x.id)
        models.sort(key=lambda x: x.id)
        
        for i, model in enumerate(models):
            assert retrieved[i].id == model.id
            assert retrieved[i].name == model.name
            assert retrieved[i].value == model.value
    
    @pytest.mark.asyncio
    async def test_async_neo4j_connection_error(self, async_model_factory):
        """Test handling of Neo4j connection errors."""
        test_model = async_model_factory(id=44, name="test_async_neo4j", value=90.12)
        
        # Mock a connection error
        with patch('neo4j.AsyncGraphDatabase.driver', side_effect=Exception("Connection error")):
            # Try to connect to an invalid Neo4j instance
            with pytest.raises(ConnectionError) as exc_info:
                await test_model.adapt_to_async(
                    obj_key="async_neo4j",
                    url="neo4j://invalid:invalid@localhost:7687",
                    label="TestModel",
                )
            assert "Neo4j" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_neo4j_resource_not_found(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test handling of resource not found errors."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        model_cls = async_model_factory(id=1, name="test1", value=1.1).__class__
        
        # Set up empty result
        async def mock_empty_aiter():
            # Empty generator
            if False:
                yield
        
        mock_result.__aiter__.return_value = mock_empty_aiter()
        
        # Try to retrieve a non-existent node
        with pytest.raises(ResourceError) as exc_info:
            await model_cls.adapt_from_async(
                {
                    "url": "bolt://localhost:7687",
                    "auth": ("neo4j", "password"),
                    "label": "NonExistentLabel",
                    "where": "n.id = 999",
                },
                obj_key="async_neo4j",
                many=False,
            )
        assert "No nodes found matching the query" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_async_neo4j_update_node(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test updating an existing node."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        
        # Create initial model
        test_model = async_model_factory(id=55, name="initial_name", value=100.0)
        
        # Save to Neo4j
        await test_model.adapt_to_async(
            obj_key="async_neo4j",
            url="bolt://localhost:7687",
            auth=("neo4j", "password"),
            label="AsyncTestModel",
        )
        
        # Create updated model with same ID
        updated_model = async_model_factory(id=55, name="updated_name", value=200.0)
        
        # Update in Neo4j
        await updated_model.adapt_to_async(
            obj_key="async_neo4j",
            url="bolt://localhost:7687",
            auth=("neo4j", "password"),
            label="AsyncTestModel",
        )
        
        # Mock the updated record for retrieval
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": 55, "name": "updated_name", "value": 200.0}
        )
        
        async def mock_updated_aiter():
            yield mock_record
            
        mock_result.__aiter__.return_value = mock_updated_aiter()
        
        # Retrieve from Neo4j
        retrieved = await AsyncTestModel.adapt_from_async(
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "AsyncTestModel",
                "where": "n.id = 55",
            },
            obj_key="async_neo4j",
            many=False,
        )
        
        # Verify retrieved model has updated values
        assert retrieved.id == 55
        assert retrieved.name == "updated_name"
        assert retrieved.value == 200.0
    
    @pytest.mark.asyncio
    async def test_async_neo4j_where_clause(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test filtering with where clause."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        model_cls = async_model_factory(id=1, name="test1", value=1.1).__class__
        
        # Create test instances with different values
        models = [
            async_model_factory(id=i, name=f"filter_{i}", value=float(i * 10))
            for i in range(10, 15)
        ]
        
        # Save all models to Neo4j
        for model in models:
            await model.adapt_to_async(
                obj_key="async_neo4j",
                url="bolt://localhost:7687",
                auth=("neo4j", "password"),
                label="AsyncTestModel",
            )
        
        # Mock filtered records
        filtered_records = []
        for i in range(12, 15):  # IDs 12, 13, 14 have values > 115
            mock_record = MagicMock()
            mock_record.__getitem__.return_value = MagicMock(
                _properties={"id": i, "name": f"filter_{i}", "value": float(i * 10)}
            )
            filtered_records.append(mock_record)
        
        async def mock_filtered_aiter():
            for record in filtered_records:
                yield record
                
        mock_result.__aiter__.return_value = mock_filtered_aiter()
        
        # Retrieve models with value > 115
        retrieved = await model_cls.adapt_from_async(
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "AsyncTestModel",
                "where": "n.value > 115",
            },
            obj_key="async_neo4j",
            many=True,
        )
        
        # Verify filtered results
        assert len(retrieved) == 3  # Should be models with IDs 12, 13, 14
        
        # Verify all retrieved models have value > 115
        for model in retrieved:
            assert model.value > 115
    
    @pytest.mark.asyncio
    async def test_async_neo4j_custom_merge_on(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test using a custom merge property."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        
        # Create test instance
        test_model = async_model_factory(id=66, name="unique_name", value=123.45)
        
        # Save to Neo4j using name as merge property
        result = await test_model.adapt_to_async(
            obj_key="async_neo4j",
            url="bolt://localhost:7687",
            auth=("neo4j", "password"),
            label="CustomLabel",
            merge_on="name",
        )
        
        assert result["merged_count"] == 1
        
        # Verify the query was constructed correctly
        mock_session.run.assert_called_with(
            "MERGE (n:`CustomLabel` {name: $val}) SET n += $props",
            val="unique_name",
            props={"id": 66, "name": "unique_name", "value": 123.45}
        )
        
        # Create another model with same name but different ID and value
        updated_model = async_model_factory(id=77, name="unique_name", value=987.65)
        
        # Update in Neo4j using name as merge property
        await updated_model.adapt_to_async(
            obj_key="async_neo4j",
            url="bolt://localhost:7687",
            auth=("neo4j", "password"),
            label="CustomLabel",
            merge_on="name",
        )
        
        # Mock the updated record for retrieval
        mock_record = MagicMock()
        mock_record.__getitem__.return_value = MagicMock(
            _properties={"id": 77, "name": "unique_name", "value": 987.65}
        )
        
        async def mock_updated_aiter():
            yield mock_record
            
        mock_result.__aiter__.return_value = mock_updated_aiter()
        
        # Retrieve from Neo4j
        retrieved = await AsyncTestModel.adapt_from_async(
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "CustomLabel",
                "where": "n.name = 'unique_name'",
            },
            obj_key="async_neo4j",
            many=False,
        )
        
        # Verify retrieved model has updated values but same name
        assert retrieved.id == 77  # Updated ID
        assert retrieved.name == "unique_name"  # Same name
        assert retrieved.value == 987.65  # Updated value
    
    @pytest.mark.asyncio
    async def test_async_neo4j_empty_result_many(
        self, async_model_factory, mock_neo4j_driver
    ):
        """Test handling of empty result set with many=True."""
        mock_driver, mock_session, mock_result = mock_neo4j_driver
        model_cls = async_model_factory(id=1, name="test1", value=1.1).__class__
        
        # Set up empty result
        async def mock_empty_aiter():
            # Empty generator
            if False:
                yield
                
        mock_result.__aiter__.return_value = mock_empty_aiter()
        
        # Try to retrieve with a condition that won't match any nodes
        result = await model_cls.adapt_from_async(
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "AsyncTestModel",
                "where": "n.id = 9999",
            },
            obj_key="async_neo4j",
            many=True,
        )
        
        # Should return an empty list
        assert isinstance(result, list)
        assert len(result) == 0