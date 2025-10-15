"""
Unit tests for AsyncQdrantAdapter.

Comprehensive test suite covering error handling, success paths, and resource management.
Target: 90%+ coverage for async_qdrant_.py

Note: Uses mocking for unit tests. Integration tests with real Qdrant are in test_integration_qdrant.py
"""

import importlib.util

from pydantic import BaseModel
import pytest
from qdrant_client.http import models as qd

from pydapter.exceptions import (
    ConnectionError,
    QueryError,
    ResourceError,
)
from pydapter.exceptions import (
    ValidationError as AdapterValidationError,
)
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter


def is_qdrant_available():
    """
    Check if qdrant-client is properly installed and can be imported.

    Returns:
        bool: True if qdrant-client is available, False otherwise.
    """
    try:
        return importlib.util.find_spec("qdrant_client") is not None
    except (ImportError, AttributeError):
        return False


# Create a pytest marker to skip tests if qdrant-client is not available
qdrant_skip_marker = pytest.mark.skipif(
    not is_qdrant_available(),
    reason="qdrant-client module not available or not properly installed",
)


class Document(BaseModel):
    """Test model for AsyncQdrantAdapter tests."""

    id: str
    text: str
    embedding: list[float]
    category: str = "general"


@qdrant_skip_marker
class TestAsyncQdrantAdapterProtocol:
    """Test AsyncQdrantAdapter protocol compliance."""

    def test_async_qdrant_adapter_protocol_compliance(self):
        """Test that AsyncQdrantAdapter follows the AsyncAdapter protocol."""
        # Check class attributes
        assert hasattr(AsyncQdrantAdapter, "adapter_key")
        assert AsyncQdrantAdapter.adapter_key == "async_qdrant"
        assert hasattr(AsyncQdrantAdapter, "obj_key")
        assert AsyncQdrantAdapter.obj_key == "async_qdrant"

        # Check required methods
        assert hasattr(AsyncQdrantAdapter, "to_obj")
        assert hasattr(AsyncQdrantAdapter, "from_obj")

        # Check method signatures
        to_obj_params = AsyncQdrantAdapter.to_obj.__code__.co_varnames
        assert "subj" in to_obj_params
        assert "collection" in to_obj_params
        assert "vector_field" in to_obj_params
        assert "url" in to_obj_params

        from_obj_params = AsyncQdrantAdapter.from_obj.__code__.co_varnames
        assert "subj_cls" in from_obj_params
        assert "obj" in from_obj_params
        assert "many" in from_obj_params


@qdrant_skip_marker
class TestAsyncQdrantAdapterErrorHandling:
    """Test AsyncQdrantAdapter error handling."""

    @pytest.mark.asyncio
    async def test_async_qdrant_missing_collection_to_obj(self):
        """Test handling of missing collection parameter in to_obj."""
        doc = Document(id="1", text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="",  # Empty collection name
                url="http://localhost:6333",
            )

        assert "Missing required parameter 'collection'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_missing_collection_from_obj(self):
        """Test handling of missing collection parameter in from_obj."""
        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.from_obj(
                Document,
                {"query_vector": [0.1, 0.2, 0.3], "url": "http://localhost:6333"},
                many=True,
            )

        assert "Missing required parameter 'collection'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_missing_query_vector(self):
        """Test handling of missing query_vector parameter."""
        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.from_obj(
                Document,
                {"collection": "test_collection", "url": "http://localhost:6333"},
                many=True,
            )

        assert "Missing required parameter 'query_vector'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_invalid_vector_type(self):
        """Test handling of non-list/tuple vector."""
        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_collection",
                    "query_vector": "not_a_vector",  # Invalid type
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        assert "Vector must be a list or tuple of numbers" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_invalid_vector_elements(self):
        """Test handling of non-numeric vector elements."""
        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_collection",
                    "query_vector": [0.1, "invalid", 0.3],  # Non-numeric element
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        assert "Vector must be a list or tuple of numbers" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_dimension_mismatch(self, mocker):
        """Test handling of vector dimension mismatch."""
        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        # Try to insert documents with different dimensions
        docs = [
            Document(id="1", text="test1", embedding=[0.1, 0.2, 0.3]),
            Document(id="2", text="test2", embedding=[0.1, 0.2, 0.3, 0.4, 0.5]),  # Different dimension
        ]

        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.to_obj(
                docs,
                collection="test_dim_mismatch",
                url="http://localhost:6333",
            )

        assert "Vector dimension mismatch" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_tuple_vector(self):
        """Test handling of tuple vector (should be valid)."""
        # Tuples should be accepted as vectors
        with pytest.raises(AdapterValidationError) as excinfo:
            # Will fail on missing collection, not vector type
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "query_vector": (0.1, 0.2, 0.3),  # Tuple instead of list
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        # Should fail on missing collection, not vector validation
        assert "Missing required parameter 'collection'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_missing_vector_field(self):
        """Test handling of missing vector field in model."""

        class DocNoVector(BaseModel):
            id: str
            text: str

        doc = DocNoVector(id="1", text="test")

        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_collection",
                vector_field="embedding",  # Field doesn't exist
                url="http://localhost:6333",
            )

        assert "Vector field 'embedding' not found in model" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_missing_id_field(self):
        """Test handling of missing ID field in model."""

        class DocNoId(BaseModel):
            text: str
            embedding: list[float]

        doc = DocNoId(text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises(AdapterValidationError) as excinfo:
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_collection",
                id_field="id",  # Field doesn't exist
                url="http://localhost:6333",
            )

        assert "ID field 'id' not found in model" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_async_qdrant_collection_not_found(self, mocker):
        """Test ResourceError for missing collection in search."""
        from qdrant_client.http.exceptions import UnexpectedResponse

        # Mock client that raises UnexpectedResponse with "not found"
        mock_client = mocker.AsyncMock()
        mock_client.search.side_effect = UnexpectedResponse(
            status_code=404,
            reason_phrase="Not Found",
            content="Collection not found",
            headers={},
        )
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(ResourceError):
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "nonexistent_collection",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        assert mock_client.close.called


@qdrant_skip_marker
class TestAsyncQdrantAdapterSuccessPaths:
    """Test AsyncQdrantAdapter success paths."""

    @pytest.mark.asyncio
    async def test_async_qdrant_upsert_single(self, mocker):
        """Test single vector upsert."""
        doc = Document(id="doc1", text="Sample text", embedding=[0.1, 0.2, 0.3])

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.to_obj(
            doc,
            collection="test_single",
            url="http://localhost:6333",
        )

        assert isinstance(result, dict)
        assert "upserted_count" in result
        assert result["upserted_count"] == 1
        assert mock_client.recreate_collection.called
        assert mock_client.upsert.called
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_upsert_batch(self, mocker):
        """Test batch vector upsert."""
        docs = [
            Document(id="doc1", text="Text 1", embedding=[0.1, 0.2, 0.3]),
            Document(id="doc2", text="Text 2", embedding=[0.2, 0.3, 0.4]),
            Document(id="doc3", text="Text 3", embedding=[0.3, 0.4, 0.5]),
        ]

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.to_obj(
            docs,
            collection="test_batch",
            url="http://localhost:6333",
        )

        assert isinstance(result, dict)
        assert "upserted_count" in result
        assert result["upserted_count"] == 3
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_search_basic(self, mocker):
        """Test basic similarity search."""
        # Mock search results
        from qdrant_client.http import models as qd

        mock_results = [
            qd.ScoredPoint(
                id="doc1",
                version=1,
                score=0.95,
                payload={
                    "id": "doc1",
                    "text": "Technology article",
                    "category": "tech",
                    "embedding": [0.1, 0.2, 0.3],
                },
                vector=None,
            ),
            qd.ScoredPoint(
                id="doc3",
                version=1,
                score=0.90,
                payload={
                    "id": "doc3",
                    "text": "Tech blog post",
                    "category": "tech",
                    "embedding": [0.15, 0.25, 0.35],
                },
                vector=None,
            ),
        ]

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=mock_results)
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        results = await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_search",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:6333",
                "top_k": 2,
            },
            many=True,
        )

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, Document) for r in results)
        assert results[0].text == "Technology article"
        assert results[0].category == "tech"
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_search_empty_results_many(self, mocker):
        """Test empty results handling with many=True."""
        # Mock empty search results
        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_empty_many",
                "query_vector": [0.9, 0.9, 0.9],
                "url": "http://localhost:6333",
                "top_k": 1,
            },
            many=True,
        )

        assert isinstance(result, list)
        assert len(result) == 0
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_search_empty_results_single(self, mocker):
        """Test empty results handling with many=False (should raise ResourceError)."""
        # Mock empty search results
        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(ResourceError) as excinfo:
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_empty_single",
                    "query_vector": [0.9, 0.9, 0.9],
                    "url": "http://localhost:6333",
                    "top_k": 1,
                },
                many=False,
            )

        assert "No points found matching the query vector" in str(excinfo.value)
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_search_single_result(self, mocker):
        """Test search with many=False returning single result."""
        # Mock single search result
        mock_result = qd.ScoredPoint(
            id="doc1",
            version=1,
            score=0.99,
            payload={
                "id": "doc1",
                "text": "Single result",
                "category": "general",
                "embedding": [0.5, 0.5, 0.5],
            },
            vector=None,
        )

        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[mock_result])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_single_result",
                "query_vector": [0.5, 0.5, 0.5],
                "url": "http://localhost:6333",
                "top_k": 1,
            },
            many=False,
        )

        assert isinstance(result, Document)
        assert result.text == "Single result"
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_custom_fields(self, mocker):
        """Test with custom vector_field and id_field."""

        class CustomDoc(BaseModel):
            doc_id: str
            content: str
            vec: list[float]

        doc = CustomDoc(doc_id="custom1", content="Custom content", vec=[0.1, 0.2, 0.3])

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.to_obj(
            doc,
            collection="test_custom_fields",
            vector_field="vec",
            id_field="doc_id",
            url="http://localhost:6333",
        )

        assert isinstance(result, dict)
        assert result["upserted_count"] == 1
        assert mock_client.close.called


@qdrant_skip_marker
class TestAsyncQdrantAdapterResourceManagement:
    """Test AsyncQdrantAdapter resource management."""

    @pytest.mark.asyncio
    async def test_async_qdrant_client_closed_to_obj(self, mocker):
        """Test that client.close() is called in to_obj (P0-3 fix)."""
        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        # Mock client with close tracking
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        await AsyncQdrantAdapter.to_obj(doc, collection="test_close", url="http://localhost:6333")

        # Verify close was called
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_client_closed_from_obj(self, mocker):
        """Test that client.close() is called in from_obj (P0-3 fix)."""
        # Mock search result
        mock_result = qd.ScoredPoint(
            id="doc1",
            version=1,
            score=0.99,
            payload={
                "id": "doc1",
                "text": "test",
                "category": "general",
                "embedding": [0.1, 0.2, 0.3],
            },
            vector=None,
        )

        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[mock_result])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_close_search",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:6333",
            },
            many=True,
        )

        # Verify close was called
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_client_closed_on_error(self, mocker):
        """Test that client.close() is called even when error occurs."""
        # Create a mock that will fail on recreate_collection but still close
        mock_client = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()

        # Make recreate_collection raise an exception
        mock_client.recreate_collection.side_effect = Exception("Test error")
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises((QueryError, Exception)):
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_error_close",
                url="http://localhost:6333",
            )

        # Verify close was still called
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_empty_items_to_obj(self):
        """Test handling of empty items list."""
        result = await AsyncQdrantAdapter.to_obj(
            [],
            collection="test_empty",
            url="http://localhost:6333",
        )

        # Should return None for empty items
        assert result is None


@qdrant_skip_marker
class TestAsyncQdrantAdapterConnectionErrors:
    """Test AsyncQdrantAdapter connection and network error handling."""

    @pytest.mark.asyncio
    async def test_async_qdrant_connection_error_on_client_creation(self, mocker):
        """Test connection error when creating client."""
        from qdrant_client.http.exceptions import UnexpectedResponse

        # Mock AsyncQdrantClient constructor to raise exception
        def mock_client_error(_url):
            raise UnexpectedResponse(
                status_code=503,
                reason_phrase="Service Unavailable",
                content="Cannot connect to Qdrant",
                headers={},
            )

        mocker.patch.object(AsyncQdrantAdapter, "_client", side_effect=mock_client_error)

        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises((ConnectionError, QueryError)) as excinfo:
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_connection",
                url="http://invalid:6333",
            )

        # Should get some error related to connection
        assert excinfo.value is not None

    @pytest.mark.asyncio
    async def test_async_qdrant_recreate_collection_error(self, mocker):
        """Test error during collection recreation."""
        from qdrant_client.http.exceptions import UnexpectedResponse

        # Mock client with failing recreate_collection
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection.side_effect = UnexpectedResponse(
            status_code=400,
            reason_phrase="Bad Request",
            content="Invalid collection configuration",
            headers={},
        )
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises(QueryError):
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_recreate_error",
                url="http://localhost:6333",
            )

        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_upsert_error(self, mocker):
        """Test error during upsert operation."""
        from qdrant_client.http.exceptions import UnexpectedResponse

        # Mock client with failing upsert
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert.side_effect = UnexpectedResponse(
            status_code=500,
            reason_phrase="Internal Server Error",
            content="Failed to upsert points",
            headers={},
        )
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        with pytest.raises(QueryError):
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_upsert_error",
                url="http://localhost:6333",
            )

        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_grpc_error_during_search(self, mocker):
        """Test gRPC error during search operation."""
        import grpc

        # Mock client with gRPC error
        mock_client = mocker.AsyncMock()
        mock_client.search.side_effect = grpc.RpcError("Connection refused")
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(ConnectionError):
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_grpc_error",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_general_search_error(self, mocker):
        """Test general exception during search operation."""
        # Mock client with general exception
        mock_client = mocker.AsyncMock()
        mock_client.search.side_effect = RuntimeError("Unexpected error")
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(QueryError):
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_general_error",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:6333",
                },
                many=True,
            )

        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_model_validation_error(self, mocker):
        """Test Pydantic validation error when converting results."""
        # Mock search result with invalid data
        mock_result = qd.ScoredPoint(
            id="doc1",
            version=1,
            score=0.99,
            payload={
                # Missing required 'id' and 'embedding' fields
                "text": "Invalid data",
            },
            vector=None,
        )

        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[mock_result])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(AdapterValidationError):
            await AsyncQdrantAdapter.from_obj(
                Document,
                {
                    "collection": "test_validation_error",
                    "query_vector": [0.1, 0.2, 0.3],
                    "url": "http://localhost:6333",
                },
                many=False,
            )

        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_point_creation_error(self, mocker):
        """Test exception during point serialization in upsert."""
        doc = Document(id="doc1", text="test", embedding=[0.1, 0.2, 0.3])

        # Mock client with upsert that raises TypeError (invalid point data)
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert.side_effect = TypeError("Invalid point data")
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        with pytest.raises(QueryError):
            await AsyncQdrantAdapter.to_obj(
                doc,
                collection="test_point_error",
                url="http://localhost:6333",
            )

        assert mock_client.close.called


@qdrant_skip_marker
class TestAsyncQdrantAdapterEdgeCases:
    """Test AsyncQdrantAdapter edge cases."""

    @pytest.mark.asyncio
    async def test_async_qdrant_large_batch(self, mocker):
        """Test handling of large batch upsert."""
        # Create 100 documents
        docs = [
            Document(id=f"doc{i}", text=f"Text {i}", embedding=[0.1 * i, 0.2 * i, 0.3 * i])
            for i in range(100)
        ]

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.to_obj(
            docs,
            collection="test_large_batch",
            url="http://localhost:6333",
        )

        assert isinstance(result, dict)
        assert result["upserted_count"] == 100
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_high_dimensional_vector(self, mocker):
        """Test handling of high-dimensional vectors."""

        class HighDimDoc(BaseModel):
            id: str
            text: str
            embedding: list[float]

        # 384-dimensional vector (common embedding size)
        embedding = [0.1] * 384
        doc = HighDimDoc(id="doc1", text="High dimensional", embedding=embedding)

        # Mock client
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        result = await AsyncQdrantAdapter.to_obj(
            doc,
            collection="test_high_dim",
            url="http://localhost:6333",
        )

        assert isinstance(result, dict)
        assert result["upserted_count"] == 1
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_search_with_top_k(self, mocker):
        """Test search with custom top_k parameter."""
        # Mock single result
        mock_result = qd.ScoredPoint(
            id="doc1",
            version=1,
            score=0.99,
            payload={
                "id": "doc1",
                "text": "Similar",
                "category": "general",
                "embedding": [0.1, 0.2, 0.3],
            },
            vector=None,
        )

        mock_client = mocker.AsyncMock()
        mock_client.search = mocker.AsyncMock(return_value=[mock_result])
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        results = await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_threshold",
                "query_vector": [0.1, 0.2, 0.3],
                "url": "http://localhost:6333",
                "top_k": 1,
            },
            many=True,
        )

        assert isinstance(results, list)
        assert len(results) == 1
        # Verify search was called with correct limit
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        assert call_args[1]["limit"] == 1
        assert mock_client.close.called

    @pytest.mark.asyncio
    async def test_async_qdrant_payload_exclude_vector(self, mocker):
        """Test that vector field is excluded from payload."""
        doc = Document(id="doc1", text="Test payload", embedding=[0.1, 0.2, 0.3], category="test")

        # Mock client and capture the upsert call
        mock_client = mocker.AsyncMock()
        mock_client.recreate_collection = mocker.AsyncMock()
        mock_client.upsert = mocker.AsyncMock()
        mock_client.close = mocker.AsyncMock()
        mocker.patch.object(AsyncQdrantAdapter, "_client", return_value=mock_client)

        await AsyncQdrantAdapter.to_obj(doc, collection="test_payload", url="http://localhost:6333")

        # Verify upsert was called and check the payload
        assert mock_client.upsert.called
        call_args = mock_client.upsert.call_args
        points = call_args[0][1]  # Second positional argument is the points list
        assert len(points) == 1
        # Payload should not include the embedding field
        assert "embedding" not in points[0].payload
        assert "text" in points[0].payload
        assert "category" in points[0].payload
        assert mock_client.close.called
