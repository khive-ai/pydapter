"""
Unit tests for WeaviateAdapter.
"""

from pydantic import BaseModel
import pytest

from pydapter.core import Adaptable
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.weaviate_ import WeaviateAdapter


# Define helper function directly in the test file
def is_weaviate_available():
    """
    Check if weaviate is properly installed and can be imported.

    Returns:
        bool: True if weaviate is available, False otherwise.
    """
    try:
        # Use importlib.util to check if the module is available without importing it
        import importlib.util

        return importlib.util.find_spec("weaviate") is not None
    except (ImportError, AttributeError):
        return False


# Create a pytest marker to skip tests if weaviate is not available
weaviate_skip_marker = pytest.mark.skipif(
    not is_weaviate_available(),
    reason="Weaviate module not available or not properly installed",
)


class TestModel(Adaptable, BaseModel):
    """Test model for WeaviateAdapter tests."""

    id: int
    name: str
    value: float
    embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]


@weaviate_skip_marker
class TestWeaviateAdapterProtocol:
    """Test WeaviateAdapter protocol compliance."""

    def test_weaviate_adapter_protocol_compliance(self):
        """Test that WeaviateAdapter follows the Adapter protocol."""
        # Check class attributes
        assert hasattr(WeaviateAdapter, "obj_key")
        assert WeaviateAdapter.obj_key == "weav"

        # Check required methods
        assert hasattr(WeaviateAdapter, "to_obj")
        assert hasattr(WeaviateAdapter, "from_obj")

        # Check method signatures
        to_obj_params = WeaviateAdapter.to_obj.__code__.co_varnames
        assert "subj" in to_obj_params
        assert "class_name" in to_obj_params
        assert "vector_field" in to_obj_params
        assert "url" in to_obj_params

        from_obj_params = WeaviateAdapter.from_obj.__code__.co_varnames
        assert "subj_cls" in from_obj_params
        assert "obj" in from_obj_params
        assert "many" in from_obj_params


@weaviate_skip_marker
class TestWeaviateAdapterFunctionality:
    """Test WeaviateAdapter functionality."""

    def test_weaviate_to_obj(self, mocker):
        """Test conversion from model to Weaviate object."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_client.collections.create.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj
        test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        # Verify the client was created with the correct URL
        WeaviateAdapter._client.assert_called_once_with("http://localhost:8080")

        # Verify collection was accessed or created
        mock_client.collections.get.assert_called_once_with("TestModel")

        # Verify data insertion
        mock_collection.data.insert.assert_called_once()

        # Verify the correct data was passed
        call_args = mock_collection.data.insert.call_args[1]

        assert isinstance(call_args["vector"], list)
        assert len(call_args["vector"]) == 5
        assert "properties" in call_args

    def test_weaviate_from_obj(self, mocker):
        """Test conversion from Weaviate object to model."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock query result
        mock_result = mocker.MagicMock()
        mock_obj = mocker.MagicMock()
        mock_obj.properties = {
            "id": 1,
            "name": "test",
            "value": 42.5,
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
        mock_result.objects = [mock_obj]
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj
        result = test_cls.adapt_from(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 1,
            },
            obj_key="weav",
            many=False,
        )

        # Verify the client was created with the correct URL
        WeaviateAdapter._client.assert_called_once_with("http://localhost:8080")

        # Verify query was constructed correctly
        mock_client.collections.get.assert_called_once_with("TestModel")
        mock_query.near_vector.assert_called_once()
        mock_query.with_additional.assert_called_once_with(["id", "vector"])
        mock_query.do.assert_called_once()

        # Verify result
        assert isinstance(result, TestModel)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5
        assert result.embedding == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_weaviate_from_obj_many(self, mocker):
        """Test conversion from multiple Weaviate objects to models."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock query result with multiple items
        mock_result = mocker.MagicMock()
        mock_obj1 = mocker.MagicMock()
        mock_obj1.properties = {
            "id": 1,
            "name": "test1",
            "value": 42.5,
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
        mock_obj2 = mocker.MagicMock()
        mock_obj2.properties = {
            "id": 2,
            "name": "test2",
            "value": 43.5,
            "embedding": [0.2, 0.3, 0.4, 0.5, 0.6],
        }
        mock_result.objects = [mock_obj1, mock_obj2]
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with many=True
        results = test_cls.adapt_from(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": "http://localhost:8080",
                "top_k": 5,
            },
            obj_key="weav",
            many=True,
        )

        # Verify query was constructed correctly
        mock_client.collections.get.assert_called_once_with("TestModel")
        mock_query.near_vector.assert_called_once()
        mock_query.with_additional.assert_called_once_with(["id", "vector"])
        mock_query.do.assert_called_once()

        # Verify results
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, TestModel) for r in results)
        assert results[0].id == 1
        assert results[0].name == "test1"
        assert results[1].id == 2
        assert results[1].name == "test2"


@weaviate_skip_marker
class TestWeaviateAdapterErrorHandling:
    """Test WeaviateAdapter error handling."""

    def test_missing_class_name_parameter(self):
        """Test handling of missing class_name parameter."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Test to_obj with missing class_name
        with pytest.raises(AdapterValidationError) as excinfo:
            test_model.adapt_to(
                obj_key="weav",
                url="http://localhost:8080",
                class_name="",  # Empty class_name
            )

        assert "Missing required parameter 'class_name'" in str(excinfo.value)

    def test_connection_error(self, mocker):
        """Test handling of connection errors."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock client creation to raise exception
        mocker.patch.object(WeaviateAdapter, "_client", side_effect=Exception("Connection failed"))

        # Test to_obj with connection error
        with pytest.raises(ConnectionError) as excinfo:
            test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://invalid-url")

        assert "Failed to connect to Weaviate" in str(excinfo.value)

    def test_query_error(self, mocker):
        """Test handling of query errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock query execution to raise exception
        mock_query.do.side_effect = Exception("Query failed")

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with query error
        with pytest.raises(QueryError) as excinfo:
            test_cls.adapt_from(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="weav",
            )

        assert "Failed to execute Weaviate query" in str(excinfo.value)

    def test_resource_not_found(self, mocker):
        """Test handling of resource not found errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.objects = []
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with empty result and many=False
        with pytest.raises(ResourceError) as excinfo:
            test_cls.adapt_from(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="weav",
                many=False,
            )

        assert "No objects found matching the query" in str(excinfo.value)

    def test_validation_error(self, mocker):
        """Test handling of validation errors."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock result with invalid data (missing required field)
        mock_result = mocker.MagicMock()
        mock_obj = mocker.MagicMock()
        mock_obj.properties = {
            "id": 1,
            # Missing "name" field
            "value": 42.5,
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
        mock_result.objects = [mock_obj]
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with validation error
        with pytest.raises(AdapterValidationError) as excinfo:
            test_cls.adapt_from(
                {
                    "class_name": "TestModel",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="weav",
                many=False,
            )

        assert "validation error" in str(excinfo.value).lower()

    def test_missing_vector_field(self, mocker):
        """Test handling of missing vector field."""

        # Create test instance without embedding field
        class TestModelNoVector(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        test_model = TestModelNoVector(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client
        mock_client = mocker.MagicMock()
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with missing vector field
        with pytest.raises(AdapterValidationError) as excinfo:
            test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        assert "Vector field 'embedding' not found in model" in str(excinfo.value)

    def test_missing_query_vector(self):
        """Test handling of missing query_vector parameter in from_obj."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Test from_obj with missing query_vector
        with pytest.raises(AdapterValidationError) as excinfo:
            test_cls.adapt_from(
                {
                    "class_name": "TestModel",
                    # Missing query_vector
                },
                obj_key="weav",
            )

        assert "Missing required parameter 'query_vector'" in str(excinfo.value)

    def test_invalid_vector_format(self, mocker):
        """Test handling of invalid vector format (not a list)."""

        # Create test instance with invalid vector
        class TestModelInvalidVector(Adaptable, BaseModel):
            id: int
            name: str
            value: float
            embedding: str  # Should be list[float]

        test_model = TestModelInvalidVector(id=1, name="test", value=42.5, embedding="not_a_list")

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with invalid vector format
        with pytest.raises(AdapterValidationError) as excinfo:
            test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        assert "must be a list of floats" in str(excinfo.value)

    def test_empty_input_list(self, mocker):
        """Test handling of empty input list to to_obj."""
        # Mock the client
        mock_client = mocker.MagicMock()
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with empty list
        result = WeaviateAdapter.to_obj(
            [], class_name="TestModel", url="http://localhost:8080", many=True
        )

        # Should return 0 count for empty input
        assert result == {"added_count": 0}

        # Client should not be called for empty input
        WeaviateAdapter._client.assert_not_called()

    def test_batch_insertion_multiple_objects(self, mocker):
        """Test batch insertion with multiple objects."""
        # Create test instances
        test_models = [
            TestModel(id=i, name=f"test{i}", value=float(i * 10), embedding=[0.1 * i] * 5)
            for i in range(1, 4)
        ]

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with multiple instances
        result = WeaviateAdapter.to_obj(
            test_models, class_name="TestModel", url="http://localhost:8080", many=True
        )

        # Verify all objects were inserted
        assert result["added_count"] == 3
        assert mock_collection.data.insert.call_count == 3

    def test_empty_results_with_many_true(self, mocker):
        """Test empty query results with many=True."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock empty result
        mock_result = mocker.MagicMock()
        mock_result.objects = []
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with empty result and many=True
        results = test_cls.adapt_from(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="weav",
            many=True,
        )

        # Should return empty list for many=True
        assert results == []

    def test_collection_creation_on_missing(self, mocker):
        """Test collection creation when it doesn't exist."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()

        # First call to get() raises exception, then create() returns collection
        mock_client.collections.get.side_effect = Exception("Collection not found")
        mock_client.collections.create.return_value = mock_collection

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj - should create collection
        test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        # Verify collection creation was attempted
        mock_client.collections.create.assert_called_once()
        mock_collection.data.insert.assert_called_once()

    def test_model_without_id_field(self, mocker):
        """Test insertion of model without id field."""

        # Create test model without id
        class TestModelNoId(Adaptable, BaseModel):
            name: str
            value: float
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        test_model = TestModelNoId(name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj
        test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        # Verify insertion was called without uuid parameter
        mock_collection.data.insert.assert_called_once()
        call_kwargs = mock_collection.data.insert.call_args[1]
        assert "uuid" not in call_kwargs

    def test_insert_operation_failure(self, mocker):
        """Test handling of insert operation failure."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection

        # Mock insert to raise exception
        mock_collection.data.insert.side_effect = Exception("Insert failed")

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with insert failure
        with pytest.raises(QueryError) as excinfo:
            test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        assert "Failed to add object to Weaviate" in str(excinfo.value)

    def test_collection_create_failure(self, mocker):
        """Test handling of collection creation failure."""
        # Create test instance
        test_model = TestModel(id=1, name="test", value=42.5)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client
        mock_client = mocker.MagicMock()

        # Both get and create fail
        mock_client.collections.get.side_effect = Exception("Collection not found")
        mock_client.collections.create.side_effect = Exception("Create failed")

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with collection creation failure
        with pytest.raises(QueryError) as excinfo:
            test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        assert "Failed to get or create collection" in str(excinfo.value)

    def test_old_api_response_format(self, mocker):
        """Test handling of old API response format."""
        # Create test class
        test_cls = TestModel

        # Register adapter
        test_cls.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_query = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query = mock_query
        mock_query.near_vector.return_value = mock_query
        mock_query.with_additional.return_value = mock_query

        # Mock query result in old API format (dict instead of object)
        mock_result = {
            "data": {
                "Get": {
                    "TestModel": [
                        {
                            "id": 1,
                            "name": "test",
                            "value": 42.5,
                            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                        }
                    ]
                }
            }
        }
        mock_query.do.return_value = mock_result

        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test from_obj with old API format
        results = test_cls.adapt_from(
            {
                "class_name": "TestModel",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="weav",
            many=True,
        )

        # Should handle old format correctly
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].name == "test"

    def test_nested_objects_handling(self, mocker):
        """Test handling of nested Pydantic models."""

        # Create nested model
        class NestedModel(BaseModel):
            nested_value: str

        class TestModelNested(Adaptable, BaseModel):
            id: int
            name: str
            nested: NestedModel
            embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]

        test_model = TestModelNested(
            id=1,
            name="test",
            nested=NestedModel(nested_value="nested_data"),
        )

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with nested model
        test_model.adapt_to(obj_key="weav", class_name="TestModel", url="http://localhost:8080")

        # Verify insertion was called
        mock_collection.data.insert.assert_called_once()
        call_kwargs = mock_collection.data.insert.call_args[1]

        # Properties should include serialized nested object
        assert "properties" in call_kwargs
        assert "nested" in call_kwargs["properties"]

    def test_large_batch_operations(self, mocker):
        """Test large batch operations."""
        # Create large batch of test instances
        test_models = [
            TestModel(id=i, name=f"test{i}", value=float(i), embedding=[0.1] * 5)
            for i in range(100)
        ]

        # Mock the client and collection
        mock_client = mocker.MagicMock()
        mock_collection = mocker.MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mocker.patch.object(WeaviateAdapter, "_client", return_value=mock_client)

        # Test to_obj with large batch
        result = WeaviateAdapter.to_obj(
            test_models, class_name="TestModel", url="http://localhost:8080", many=True
        )

        # Verify all objects were inserted
        assert result["added_count"] == 100
        assert mock_collection.data.insert.call_count == 100
