"""
Unit tests for AsyncWeaviateAdapter.

Comprehensive test suite covering error handling, success paths, and resource management.
Target: 90%+ coverage for async_weaviate_.py

Note: Uses mocking for unit tests. Integration tests with real Weaviate are separate.
"""

import importlib.util

from aiohttp import ClientError
from pydantic import BaseModel
import pytest

from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.async_weaviate_ import AsyncWeaviateAdapter


def is_weaviate_available():
    """Check if weaviate is properly installed and can be imported."""
    try:
        return importlib.util.find_spec("weaviate") is not None
    except (ImportError, AttributeError):
        return False


weaviate_skip_marker = pytest.mark.skipif(
    not is_weaviate_available(),
    reason="Weaviate module not available or not properly installed",
)


class Document(BaseModel):
    """Test model for AsyncWeaviateAdapter tests."""

    id: int
    name: str
    value: float
    embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]


def create_mock_session(mocker, get_status=200, get_response=None, post_responses=None):
    """Helper to create a properly mocked aiohttp ClientSession."""
    # Create session mock - use MagicMock for the session itself
    mock_session = mocker.MagicMock()
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=None)

    # Mock GET
    mock_get_response = mocker.AsyncMock()
    mock_get_response.status = get_status
    if get_response:
        mock_get_response.json = mocker.AsyncMock(return_value=get_response)

    # Use MagicMock for the context manager wrapper, AsyncMock for __aenter__/__aexit__
    mock_get_cm = mocker.MagicMock()
    mock_get_cm.__aenter__ = mocker.AsyncMock(return_value=mock_get_response)
    mock_get_cm.__aexit__ = mocker.AsyncMock(return_value=None)
    mock_session.get.return_value = mock_get_cm

    # Mock POST
    if post_responses:
        if isinstance(post_responses, list):
            # Multiple POST responses
            post_calls = [0]

            def post_side_effect(*args, **kwargs):
                idx = post_calls[0]
                post_calls[0] += 1
                mock_post_cm = mocker.MagicMock()
                if idx < len(post_responses):
                    mock_post_cm.__aenter__ = mocker.AsyncMock(return_value=post_responses[idx])
                else:
                    mock_post_cm.__aenter__ = mocker.AsyncMock(return_value=post_responses[-1])
                mock_post_cm.__aexit__ = mocker.AsyncMock(return_value=None)
                return mock_post_cm

            mock_session.post.side_effect = post_side_effect
        else:
            # Single POST response
            mock_post_cm = mocker.MagicMock()
            mock_post_cm.__aenter__ = mocker.AsyncMock(return_value=post_responses)
            mock_post_cm.__aexit__ = mocker.AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_cm

    return mock_session


@weaviate_skip_marker
class TestAsyncWeaviateAdapterProtocol:
    """Test AsyncWeaviateAdapter protocol compliance."""

    def test_async_weaviate_adapter_protocol_compliance(self):
        """Test that AsyncWeaviateAdapter follows the AsyncAdapter protocol."""
        assert hasattr(AsyncWeaviateAdapter, "obj_key")
        assert AsyncWeaviateAdapter.obj_key == "async_weav"

        assert hasattr(AsyncWeaviateAdapter, "to_obj")
        assert hasattr(AsyncWeaviateAdapter, "from_obj")

        to_obj_params = AsyncWeaviateAdapter.to_obj.__code__.co_varnames
        assert "subj" in to_obj_params
        assert "class_name" in to_obj_params

        from_obj_params = AsyncWeaviateAdapter.from_obj.__code__.co_varnames
        assert "subj_cls" in from_obj_params
        assert "obj" in from_obj_params


@weaviate_skip_marker
class TestAsyncWeaviateAdapterErrorHandling:
    """Test AsyncWeaviateAdapter error handling."""

    @pytest.mark.asyncio
    async def test_async_weaviate_missing_class_name(self):
        """Test handling of missing class_name parameter in to_obj."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        with pytest.raises(AdapterValidationError, match="class_name"):
            await AsyncWeaviateAdapter.to_obj(doc, class_name="", url="http://localhost:8080")

    @pytest.mark.asyncio
    async def test_async_weaviate_missing_url(self):
        """Test handling of missing url parameter in to_obj."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        with pytest.raises(AdapterValidationError, match="url"):
            await AsyncWeaviateAdapter.to_obj(doc, class_name="TestClass", url="")

    @pytest.mark.asyncio
    async def test_async_weaviate_missing_class_name_from_obj(self):
        """Test handling of missing class_name parameter in from_obj."""
        with pytest.raises(AdapterValidationError, match="class_name"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {"query_vector": [0.1, 0.2, 0.3], "url": "http://localhost:8080"},
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_missing_query_vector(self):
        """Test handling of missing query_vector parameter."""
        with pytest.raises(AdapterValidationError, match="query_vector"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {"class_name": "TestClass", "url": "http://localhost:8080"},
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_connection_error(self, mocker):
        """Test handling of connection failure during to_obj."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        mock_session = mocker.MagicMock()
        mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_get_cm = mocker.MagicMock()
        mock_get_cm.__aenter__ = mocker.AsyncMock(side_effect=ClientError("Connection failed"))
        mock_get_cm.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_cm

        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(ConnectionError, match="Failed to connect to Weaviate"):
            await AsyncWeaviateAdapter.to_obj(
                doc, class_name="TestClass", url="http://localhost:8080"
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_class_not_found(self, mocker):
        """Test ResourceError for missing class in from_obj."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={
                "errors": [{"message": "Cannot query field 'NonExistent' on type 'GetObjectsObj'"}]
            }
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(ResourceError, match="does not exist"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "NonExistent",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_validation_error(self, mocker):
        """Test Pydantic validation failure when converting results."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {"TestClass": [{"_additional": {"id": "uuid"}, "embedding": [0.1]}]}
                }
            }
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(AdapterValidationError, match="Validation error"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=False,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_invalid_vector(self, mocker):
        """Test handling of invalid vector format."""

        class DocInvalidVector(BaseModel):
            id: int
            name: str
            embedding: str  # Wrong type

        doc = DocInvalidVector(id=1, name="test", embedding="not_a_vector")

        mock_session = create_mock_session(mocker, get_status=200)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(AdapterValidationError, match="must be a list of floats"):
            await AsyncWeaviateAdapter.to_obj(
                doc, class_name="TestClass", url="http://localhost:8080"
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_empty_results_many_true(self, mocker):
        """Test empty results handling with many=True."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={"data": {"Get": {"TestClass": []}}}
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.from_obj(
            Document,
            {
                "class_name": "TestClass",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:8080",
            },
            many=True,
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_async_weaviate_empty_results_many_false(self, mocker):
        """Test empty results handling with many=False (should raise ResourceError)."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={"data": {"Get": {"TestClass": []}}}
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(ResourceError, match="No objects found"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=False,
            )


@weaviate_skip_marker
class TestAsyncWeaviateAdapterSuccessPaths:
    """Test AsyncWeaviateAdapter success paths."""

    @pytest.mark.asyncio
    async def test_async_weaviate_insert_single(self, mocker):
        """Test single object insertion."""
        doc = Document(id=1, name="test doc", value=42.5, embedding=[0.1, 0.2, 0.3])

        mock_post_schema = mocker.AsyncMock()
        mock_post_schema.status = 201

        mock_post_object = mocker.AsyncMock()
        mock_post_object.status = 201

        mock_session = create_mock_session(
            mocker, get_status=404, post_responses=[mock_post_schema, mock_post_object]
        )
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.to_obj(
            doc, class_name="TestClass", url="http://localhost:8080"
        )

        assert result["added_count"] == 1

    @pytest.mark.asyncio
    async def test_async_weaviate_insert_batch(self, mocker):
        """Test batch insertion of multiple objects."""
        docs = [
            Document(id=i, name=f"doc{i}", value=float(i), embedding=[0.1, 0.2, 0.3])
            for i in range(3)
        ]

        mock_post_object = mocker.AsyncMock()
        mock_post_object.status = 201

        mock_session = create_mock_session(mocker, get_status=200, post_responses=mock_post_object)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.to_obj(
            docs, class_name="TestClass", url="http://localhost:8080"
        )

        assert result["added_count"] == 3

    @pytest.mark.asyncio
    async def test_async_weaviate_query_basic(self, mocker):
        """Test basic similarity query."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {
                        "TestClass": [
                            {
                                "_additional": {"id": "uuid-1", "vector": [0.1, 0.2, 0.3]},
                                "name": "result1",
                                "value": 10.0,
                            }
                        ]
                    }
                }
            }
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        results = await AsyncWeaviateAdapter.from_obj(
            Document,
            {
                "class_name": "TestClass",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:8080",
                "top_k": 1,
            },
            many=True,
        )

        assert len(results) == 1
        assert results[0].name == "result1"

    @pytest.mark.asyncio
    async def test_async_weaviate_query_with_filter(self, mocker):
        """Test query with custom top_k parameter."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {
                        "TestClass": [
                            {
                                "_additional": {"id": "uuid-1", "vector": [0.1, 0.2, 0.3]},
                                "name": "result1",
                                "value": 10.0,
                            },
                            {
                                "_additional": {"id": "uuid-2", "vector": [0.2, 0.3, 0.4]},
                                "name": "result2",
                                "value": 20.0,
                            },
                        ]
                    }
                }
            }
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        results = await AsyncWeaviateAdapter.from_obj(
            Document,
            {
                "class_name": "TestClass",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:8080",
                "top_k": 2,
            },
            many=True,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_async_weaviate_vector_search(self, mocker):
        """Test vector similarity search with single result."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={
                "data": {
                    "Get": {
                        "TestClass": [
                            {
                                "_additional": {"id": "uuid", "vector": [0.5, 0.5, 0.5]},
                                "name": "similar doc",
                                "value": 99.9,
                            }
                        ]
                    }
                }
            }
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.from_obj(
            Document,
            {
                "class_name": "TestClass",
                "query_vector": [0.5, 0.5, 0.5],
                "url": "http://localhost:8080",
                "top_k": 1,
            },
            many=False,
        )

        assert result.name == "similar doc"
        assert result.value == 99.9


@weaviate_skip_marker
class TestAsyncWeaviateAdapterEdgeCases:
    """Test AsyncWeaviateAdapter edge cases."""

    @pytest.mark.asyncio
    async def test_async_weaviate_nested_objects(self, mocker):
        """Test handling of nested Pydantic models."""

        class NestedModel(BaseModel):
            inner_id: int

        class ParentModel(BaseModel):
            id: int
            name: str
            nested: NestedModel
            embedding: list[float]

        doc = ParentModel(
            id=1, name="parent", nested=NestedModel(inner_id=2), embedding=[0.1, 0.2, 0.3]
        )

        mock_post_object = mocker.AsyncMock()
        mock_post_object.status = 201

        mock_session = create_mock_session(mocker, get_status=200, post_responses=mock_post_object)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.to_obj(
            doc, class_name="ParentClass", url="http://localhost:8080"
        )

        assert result["added_count"] == 1

    @pytest.mark.asyncio
    async def test_async_weaviate_large_batch(self, mocker):
        """Test handling of large batch operations."""
        docs = [
            Document(id=i, name=f"doc{i}", value=float(i), embedding=[0.1, 0.2, 0.3])
            for i in range(50)
        ]

        mock_post_object = mocker.AsyncMock()
        mock_post_object.status = 201

        mock_session = create_mock_session(mocker, get_status=200, post_responses=mock_post_object)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.to_obj(
            docs, class_name="TestClass", url="http://localhost:8080"
        )

        assert result["added_count"] == 50

    @pytest.mark.asyncio
    async def test_async_weaviate_invalid_class_name_characters(self):
        """Test validation of class_name with invalid characters."""
        with pytest.raises(AdapterValidationError, match="Invalid class_name.*alphanumeric"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "Test-Class!@#",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_invalid_top_k_negative(self):
        """Test validation of negative top_k parameter."""
        with pytest.raises(AdapterValidationError, match="Invalid top_k.*positive integer"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                    "top_k": -1,
                },
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_invalid_top_k_non_numeric(self):
        """Test validation of non-numeric top_k parameter."""
        with pytest.raises(AdapterValidationError, match="Invalid top_k"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                    "top_k": "invalid",
                },
                many=True,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_missing_vector_field(self, mocker):
        """Test handling of missing vector field in model."""

        class DocNoVector(BaseModel):
            id: int
            name: str
            value: float

        doc = DocNoVector(id=1, name="test", value=42.0)

        mock_session = create_mock_session(mocker, get_status=200)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(AdapterValidationError, match="Vector field.*not found"):
            await AsyncWeaviateAdapter.to_obj(
                doc, class_name="TestClass", vector_field="embedding", url="http://localhost:8080"
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_create_only_mode(self, mocker):
        """Test create_only mode that only creates class without adding objects."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        mock_post_schema = mocker.AsyncMock()
        mock_post_schema.status = 201

        mock_session = create_mock_session(mocker, get_status=404, post_responses=mock_post_schema)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        result = await AsyncWeaviateAdapter.to_obj(
            doc, class_name="TestClass", url="http://localhost:8080", create_only=True
        )

        assert result["added_count"] == 0
        assert result["class_created"] is True

    @pytest.mark.asyncio
    async def test_async_weaviate_empty_items(self):
        """Test handling of empty items list."""
        result = await AsyncWeaviateAdapter.to_obj(
            [], class_name="TestClass", url="http://localhost:8080"
        )

        assert result["added_count"] == 0

    @pytest.mark.asyncio
    async def test_async_weaviate_graphql_syntax_error(self, mocker):
        """Test handling of GraphQL syntax errors."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 200
        mock_post_response.json = mocker.AsyncMock(
            return_value={"errors": [{"message": "Syntax error in GraphQL query"}]}
        )

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(QueryError, match="GraphQL error"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=False,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_schema_creation_error(self, mocker):
        """Test handling of schema creation failure."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        mock_post_schema = mocker.AsyncMock()
        mock_post_schema.status = 400
        mock_post_schema.text = mocker.AsyncMock(return_value="Invalid schema")

        mock_session = create_mock_session(mocker, get_status=404, post_responses=mock_post_schema)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(QueryError, match="Failed to create collection"):
            await AsyncWeaviateAdapter.to_obj(
                doc, class_name="TestClass", url="http://localhost:8080"
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_object_addition_error(self, mocker):
        """Test handling of object addition failure."""
        doc = Document(id=1, name="test", value=42.0, embedding=[0.1, 0.2, 0.3])

        mock_post_object = mocker.AsyncMock()
        mock_post_object.status = 500
        mock_post_object.text = mocker.AsyncMock(return_value="Internal server error")

        mock_session = create_mock_session(mocker, get_status=200, post_responses=mock_post_object)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(QueryError, match="Failed to add object"):
            await AsyncWeaviateAdapter.to_obj(
                doc, class_name="TestClass", url="http://localhost:8080"
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_query_execution_error(self, mocker):
        """Test handling of query execution failure."""
        mock_post_response = mocker.AsyncMock()
        mock_post_response.status = 500
        mock_post_response.text = mocker.AsyncMock(return_value="Internal server error")

        mock_session = create_mock_session(mocker, post_responses=mock_post_response)
        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(QueryError, match="Failed to execute Weaviate query"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=False,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_connection_error_in_from_obj(self, mocker):
        """Test handling of connection errors in from_obj."""
        mock_session = mocker.MagicMock()
        mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_post_cm = mocker.MagicMock()
        mock_post_cm.__aenter__ = mocker.AsyncMock(side_effect=ClientError("Network error"))
        mock_post_cm.__aexit__ = mocker.AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_cm

        mocker.patch("aiohttp.ClientSession", return_value=mock_session)

        with pytest.raises(ConnectionError, match="Failed to connect to Weaviate"):
            await AsyncWeaviateAdapter.from_obj(
                Document,
                {
                    "class_name": "TestClass",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:8080",
                },
                many=False,
            )
