"""
Unit tests for AsyncNeo4jAdapter.
"""

import pytest
from pydantic import BaseModel
from unittest.mock import AsyncMock, MagicMock

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import (
    ConnectionError,
    QueryError,
    ResourceError,
    ValidationError as AdapterValidationError,
)
from pydapter.extras.async_neo4j_ import AsyncNeo4jAdapter


@pytest.fixture
def async_neo4j_model_factory():
    """Factory for creating test models with AsyncNeo4jAdapter registered."""

    def create_model(**kw):
        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the AsyncNeo4j adapter
        TestModel.register_async_adapter(AsyncNeo4jAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def async_neo4j_sample(async_neo4j_model_factory):
    """Create a sample model instance."""
    return async_neo4j_model_factory(id=1, name="test", value=42.5)


class TestAsyncNeo4jAdapterProtocol:
    """Tests for AsyncNeo4jAdapter protocol compliance."""

    def test_async_neo4j_adapter_protocol_compliance(self):
        """Test that AsyncNeo4jAdapter implements the AsyncAdapter protocol."""
        # Verify required attributes
        assert hasattr(AsyncNeo4jAdapter, "obj_key")
        assert isinstance(AsyncNeo4jAdapter.obj_key, str)
        assert AsyncNeo4jAdapter.obj_key == "async_neo4j"

        # Verify method signatures
        assert hasattr(AsyncNeo4jAdapter, "from_obj")
        assert hasattr(AsyncNeo4jAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(AsyncNeo4jAdapter.from_obj)
        assert callable(AsyncNeo4jAdapter.to_obj)


class TestAsyncNeo4jAdapterFunctionality:
    """Tests for AsyncNeo4jAdapter functionality."""

    @pytest.mark.asyncio
    async def test_async_neo4j_to_obj(self, mocker, async_neo4j_sample):
        """Test conversion from model to Neo4j node."""
        # Mock the to_obj method directly
        mock_result = {"merged_count": 1}
        mocker.patch.object(
            AsyncNeo4jAdapter, "to_obj", return_value=mock_result
        )
        
        # Test to_obj
        result = await async_neo4j_sample.adapt_to_async(
            obj_key="async_neo4j", 
            url="neo4j://localhost:7687",
            auth=("neo4j", "password")
        )
        
        # Verify the result
        assert isinstance(result, dict)
        assert "merged_count" in result
        assert result["merged_count"] == 1
        
        # Verify the mock was called with the correct arguments
        mock_to_obj = AsyncNeo4jAdapter.to_obj
        assert mock_to_obj.called
        assert mock_to_obj.call_count == 1

    @pytest.mark.asyncio
    async def test_async_neo4j_from_obj(self, mocker, async_neo4j_sample):
        """Test conversion from Neo4j node to model."""
        # Mock the from_obj method directly
        mock_model = async_neo4j_sample
        mocker.patch.object(
            AsyncNeo4jAdapter, "from_obj", return_value=mock_model
        )
        
        # Test from_obj
        model_cls = async_neo4j_sample.__class__
        result = await model_cls.adapt_from_async(
            {
                "url": "neo4j://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "TestModel",
                "where": "n.id = 1"
            },
            obj_key="async_neo4j",
            many=False
        )
        
        # Verify the result
        assert isinstance(result, model_cls)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5
        
        # Verify the mock was called with the correct arguments
        mock_from_obj = AsyncNeo4jAdapter.from_obj
        assert mock_from_obj.called
        assert mock_from_obj.call_count == 1

    @pytest.mark.asyncio
    async def test_async_neo4j_from_obj_many(self, mocker, async_neo4j_sample):
        """Test conversion from Neo4j nodes to models with many=True."""
        # Mock the _create_driver method
        # Mock the from_obj method directly
        model_cls = async_neo4j_sample.__class__
        mock_models = [
            model_cls(id=1, name="test1", value=42.5),
            model_cls(id=2, name="test2", value=43.5)
        ]
        mocker.patch.object(
            AsyncNeo4jAdapter, "from_obj", return_value=mock_models
        )
        # Test from_obj with many=True
        model_cls = async_neo4j_sample.__class__
        result = await model_cls.adapt_from_async(
            {
                "url": "neo4j://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "TestModel"
            },
            obj_key="async_neo4j",
            many=True
        )
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, model_cls) for item in result)
        assert result[0].id == 1
        assert result[0].name == "test1"
        assert result[0].value == 42.5
        assert result[1].id == 2
        assert result[1].name == "test2"
        assert result[1].value == 43.5


class TestAsyncNeo4jAdapterErrorHandling:
    """Tests for AsyncNeo4jAdapter error handling."""

    @pytest.mark.asyncio
    async def test_missing_url_parameter(self, async_neo4j_sample):
        """Test that missing URL parameter raises AdapterValidationError."""
        model_cls = async_neo4j_sample.__class__
        
        with pytest.raises(AdapterValidationError) as exc_info:
            await model_cls.adapt_from_async(
                {},  # Missing url parameter
                obj_key="async_neo4j"
            )
        
        assert "Missing required parameter 'url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_error(self, mocker, async_neo4j_sample):
        """Test handling of Neo4j connection errors."""
        # Mock the _create_driver method to raise a ConnectionError
        mocker.patch.object(
            AsyncNeo4jAdapter,
            "_create_driver",
            side_effect=ConnectionError("Connection failed", adapter="async_neo4j")
        )
        
        # Test to_obj with connection error
        with pytest.raises(ConnectionError) as exc_info:
            await async_neo4j_sample.adapt_to_async(
                obj_key="async_neo4j",
                url="neo4j://invalid:7687"
            )
        
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cypher_syntax_error(self, mocker, async_neo4j_sample):
        """Test handling of Cypher syntax errors."""
        # Mock the to_obj method to raise a QueryError with Cypher syntax error
        cypher_error = QueryError(
            "Neo4j Cypher syntax error: Invalid syntax",
            query="MERGE (n:`TestModel` {id: $val}) SET n += $props",
            adapter="async_neo4j"
        )
        mocker.patch.object(
            AsyncNeo4jAdapter, "to_obj", side_effect=cypher_error
        )
        
        # Test to_obj with Cypher syntax error
        with pytest.raises(QueryError) as exc_info:
            await async_neo4j_sample.adapt_to_async(
                obj_key="async_neo4j",
                url="neo4j://localhost:7687"
            )
        
        assert "Cypher syntax error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resource_not_found(self, mocker, async_neo4j_sample):
        """Test handling of resource not found errors."""
        # Mock the from_obj method to raise a ResourceError
        resource_error = ResourceError(
            "No nodes found matching the query",
            resource="NonExistentLabel",
            where="n.id = 999"
        )
        mocker.patch.object(
            AsyncNeo4jAdapter, "from_obj", side_effect=resource_error
        )
        
        # Test from_obj with no results
        model_cls = async_neo4j_sample.__class__
        with pytest.raises(ResourceError) as exc_info:
            await model_cls.adapt_from_async(
                {
                    "url": "neo4j://localhost:7687",
                    "label": "NonExistentLabel",
                    "where": "n.id = 999"
                },
                obj_key="async_neo4j",
                many=False
            )
        
        assert "No nodes found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error(self, mocker, async_neo4j_sample):
        """Test handling of validation errors."""
        # Mock the from_obj method to raise a ValidationError
        validation_error = AdapterValidationError(
            "Validation error: 1 validation error for TestModel\nid\n  Field required [type=missing,input_value={'name': 'test'},input_type=dict]",
            data={"name": "test"},
            errors=[{"loc": ("id",), "msg": "Field required", "type": "missing"}]
        )
        mocker.patch.object(
            AsyncNeo4jAdapter, "from_obj", side_effect=validation_error
        )
        
        # Test from_obj with invalid data
        model_cls = async_neo4j_sample.__class__
        with pytest.raises(AdapterValidationError) as exc_info:
            await model_cls.adapt_from_async(
                {
                    "url": "neo4j://localhost:7687",
                    "label": "TestModel"
                },
                obj_key="async_neo4j",
                many=False
            )
        
        assert "Validation error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cypher_injection_prevention(self, async_neo4j_sample):
        """Test that the _validate_cypher method prevents injection."""
        # Test with a potentially dangerous query
        dangerous_query = "MATCH (n:`User```) RETURN n"
        
        with pytest.raises(QueryError) as exc_info:
            AsyncNeo4jAdapter._validate_cypher(dangerous_query)
        
        assert "Possible injection" in str(exc_info.value)