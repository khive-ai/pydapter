"""
Unit tests for AsyncWeaviateAdapter.
"""

import json

import aiohttp
import pytest
from pydantic import BaseModel

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.async_weaviate_ import AsyncWeaviateAdapter


class TestModel(AsyncAdaptable, BaseModel):
    """Test model for AsyncWeaviateAdapter tests."""
    id: int
    name: str
    value: float
    embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]


class TestAsyncWeaviateAdapterProtocol:
    """Test AsyncWeaviateAdapter protocol compliance."""

    def test_async_weaviate_adapter_protocol_compliance(self):
        """Test that AsyncWeaviateAdapter follows the AsyncAdapter protocol."""
        # Check class attributes
        assert hasattr(AsyncWeaviateAdapter, "obj_key")
        assert AsyncWeaviateAdapter.obj_key == "async_weav"

        # Check required methods
        assert hasattr(AsyncWeaviateAdapter, "to_obj")
        assert hasattr(AsyncWeaviateAdapter, "from_obj")

        # Check method signatures
        to_obj_params = AsyncWeaviateAdapter.to_obj.__code__.co_varnames
        assert "subj" in to_obj_params
        assert "class_name" in to_obj_params
        assert "vector_field" in to_obj_params
        assert "url" in to_obj_params

        from_obj_params = AsyncWeaviateAdapter.from_obj.__code__.co_varnames
        assert "subj_cls" in from_obj_params
        assert "obj" in from_obj_params
        assert "many" in from_obj_params


class TestAsyncWeaviateAdapterFunctionality:
    """Test AsyncWeaviateAdapter functionality."""

    @pytest.mark.asyncio
    async def test_async_weaviate_to_obj(self, mocker):
        """Test conversion from model to Weaviate object."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to return a successful result
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "to_obj",
            return_value={"added_count": 1}
        )

        # Test to_obj
        result = await test_model.adapt_to_async(
            obj_key="async_weav",
            class_name="TestModel",
            url="http://localhost:8080"
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.to_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.to_obj.call_args
        assert call_args[0][0] == test_model
        assert call_args[1]["class_name"] == "TestModel"
        assert call_args[1]["url"] == "http://localhost:8080"
        
        # Verify result
        assert isinstance(result, dict)
        assert result["added_count"] == 1

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj(self, mocker):
        """Test conversion from Weaviate object to model."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create expected result
        expected_result = TestModel(id=1, name="test", value=42.5)

        # Mock the from_obj method to return the expected result
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            return_value=expected_result
        )

        # Test from_obj
        result = await test_cls.adapt_from_async(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 1
            },
            obj_key="async_weav",
            many=False
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.from_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.from_obj.call_args
        assert call_args[0][0] == test_cls
        assert call_args[0][1]["class_name"] == "TestModel"
        assert call_args[0][1]["query_vector"] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert call_args[0][1]["url"] == "http://localhost:8080"
        assert call_args[0][1]["top_k"] == 1
        assert call_args[1]["many"] == False
        
        # Verify result
        assert isinstance(result, TestModel)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    @pytest.mark.asyncio
    async def test_async_weaviate_from_obj_many(self, mocker):
        """Test conversion from multiple Weaviate objects to models."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create expected results
        expected_results = [
            TestModel(id=1, name="test1", value=42.5),
            TestModel(id=2, name="test2", value=43.5)
        ]

        # Mock the from_obj method to return the expected results
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            return_value=expected_results
        )

        # Test from_obj with many=True
        results = await test_cls.adapt_from_async(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 5
            },
            obj_key="async_weav",
            many=True
        )

        # Verify the method was called with correct parameters
        AsyncWeaviateAdapter.from_obj.assert_called_once()
        call_args = AsyncWeaviateAdapter.from_obj.call_args
        assert call_args[0][0] == test_cls
        assert call_args[0][1]["class_name"] == "TestModel"
        assert call_args[0][1]["query_vector"] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert call_args[0][1]["url"] == "http://localhost:8080"
        assert call_args[0][1]["top_k"] == 5
        assert call_args[1]["many"] == True
        
        # Verify results
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, TestModel) for r in results)
        assert results[0].id == 1
        assert results[0].name == "test1"
        assert results[1].id == 2
        assert results[1].name == "test2"


class TestAsyncWeaviateAdapterErrorHandling:
    """Test AsyncWeaviateAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_class_name_parameter(self):
        """Test handling of missing class_name parameter."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Test to_obj with missing class_name
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                url="http://localhost:8080",
                class_name=""  # Empty class_name
            )
        
        assert "Missing required parameter 'class_name'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_missing_url_parameter(self):
        """Test handling of missing url parameter."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Test to_obj with missing url
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                class_name="TestModel",
                url=""  # Empty URL
            )
        
        assert "Missing required parameter 'url'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_connection_error(self, mocker):
        """Test handling of connection errors."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to raise ConnectionError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "to_obj",
            side_effect=ConnectionError("Failed to connect to Weaviate: Connection failed", adapter="async_weav")
        )

        # Test to_obj with connection error
        with pytest.raises(ConnectionError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                class_name="TestModel",
                url="http://invalid-url"
            )
        
        assert "Failed to connect to Weaviate" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_query_error(self, mocker):
        """Test handling of query errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise QueryError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=QueryError("Error in Weaviate query: Bad request", adapter="async_weav")
        )

        # Test from_obj with query error
        with pytest.raises(QueryError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080"
                },
                obj_key="async_weav"
            )
        
        assert "Error in Weaviate query" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_resource_not_found(self, mocker):
        """Test handling of resource not found errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise ResourceError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=ResourceError("No objects found matching the query", resource="TestModel")
        )

        # Test from_obj with empty result and many=False
        with pytest.raises(ResourceError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080"
                },
                obj_key="async_weav",
                many=False
            )
        
        assert "No objects found matching the query" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_validation_error(self, mocker):
        """Test handling of validation errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the from_obj method to raise AdapterValidationError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "from_obj",
            side_effect=AdapterValidationError("Validation error: missing required field 'name'")
        )

        # Test from_obj with validation error
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_cls.adapt_from_async(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "url": "http://localhost:8080"
                },
                obj_key="async_weav",
                many=False
            )
        
        assert "Validation error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_missing_vector_field(self, mocker):
        """Test handling of missing vector field."""
        # Create test instance without embedding field
        class TestModelNoVector(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float
        
        test_model = TestModelNoVector(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Mock the to_obj method to raise AdapterValidationError
        mocker.patch.object(
            AsyncWeaviateAdapter,
            "to_obj",
            side_effect=AdapterValidationError("Vector field 'embedding' not found in model")
        )

        # Test to_obj with missing vector field
        with pytest.raises(AdapterValidationError) as excinfo:
            await test_model.adapt_to_async(
                obj_key="async_weav",
                class_name="TestModel",
                url="http://localhost:8080"
            )
        
        assert "Vector field 'embedding' not found in model" in str(excinfo.value)