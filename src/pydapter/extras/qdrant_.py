"""
Qdrant vector-store adapter (requires `qdrant-client`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import ClassVar, TypeVar

import grpc
from pydantic import BaseModel, ValidationError
from qdrant_client import QdrantClient
from qdrant_client.http import models as qd
from qdrant_client.http.exceptions import UnexpectedResponse

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import ConnectionError, PydapterError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class QdrantAdapter(AdapterBase, Adapter[T]):
    """
    Qdrant vector database adapter for converting between Pydantic models and vector embeddings.

    This adapter provides methods to:
    - Search for similar vectors and convert results to Pydantic models
    - Insert Pydantic models as vector points into Qdrant collections
    - Handle vector similarity operations and metadata filtering
    - Support for both cloud and self-hosted Qdrant instances

    Attributes:
        adapter_key: The key identifier for this adapter type ("qdrant")
        obj_key: Legacy key identifier (for backward compatibility)

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.extras.qdrant_ import QdrantAdapter

        class Document(BaseModel):
            id: str
            text: str
            embedding: list[float]
            category: str

        # Search for similar vectors
        search_config = {
            "url": "http://localhost:6333",
            "collection_name": "documents",
            "query_vector": [0.1, 0.2, 0.3, ...],  # 768-dim vector
            "limit": 10,
            "score_threshold": 0.8
        }
        similar_docs = QdrantAdapter.from_obj(Document, search_config, many=True)

        # Insert documents with vectors
        insert_config = {
            "url": "http://localhost:6333",
            "collection_name": "documents"
        }
        new_docs = [Document(
            id="doc1",
            text="Sample text",
            embedding=[0.1, 0.2, 0.3, ...],
            category="tech"
        )]
        QdrantAdapter.to_obj(new_docs, insert_config, many=True)
        ```
    """

    adapter_key: ClassVar[str] = "qdrant"
    obj_key: ClassVar[str] = "qdrant"  # Backward compatibility

    @classmethod
    def _client(cls, url: str | None):
        """
        Create a Qdrant client with proper error handling.

        Args:
            url: Qdrant server URL or None for in-memory instance

        Returns:
            QdrantClient instance

        Raises:
            ConnectionError: If connection cannot be established
        """
        try:
            return QdrantClient(url=url) if url else QdrantClient(":memory:")
        except UnexpectedResponse as e:
            raise ConnectionError(
                f"Failed to connect to Qdrant: {e}", adapter="qdrant", url=url
            ) from e
        except (ConnectionRefusedError, OSError, grpc.RpcError) as e:
            # Catch specific network-related errors like DNS resolution failures
            # Include grpc.RpcError to handle gRPC-specific connection issues
            raise ConnectionError(
                f"Failed to connect to Qdrant: {e}", adapter="qdrant", url=url
            ) from e
        except Exception as e:
            # Check for DNS resolution errors in the exception message
            if (
                "nodename nor servname provided" in str(e)
                or "Name or service not known" in str(e)
                or "getaddrinfo failed" in str(e)
            ):
                raise ConnectionError(
                    f"DNS resolution failed for Qdrant: {e}", adapter="qdrant", url=url
                ) from e
            raise ConnectionError(
                f"Unexpected error connecting to Qdrant: {e}", adapter="qdrant", url=url
            ) from e

    @classmethod
    def _validate_vector_dimensions(cls, vector, expected_dim=None):
        """Validate that the vector has the correct dimensions."""
        if not isinstance(vector, list | tuple) or not all(
            isinstance(x, int | float) for x in vector
        ):
            raise AdapterValidationError(
                "Vector must be a list or tuple of numbers",
                data=vector,
            )

        if expected_dim is not None and len(vector) != expected_dim:
            raise AdapterValidationError(
                f"Vector dimension mismatch: expected {expected_dim}, got {len(vector)}",
                data=vector,
            )

    # outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        collection,
        vector_field="embedding",
        id_field="id",
        url=None,
        many: bool = True,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> dict | None:
        try:
            # Validate required parameters
            if not collection:
                raise AdapterValidationError("Missing required parameter 'collection'")

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return None  # Nothing to insert

            # Validate vector field exists
            if not hasattr(items[0], vector_field):
                raise AdapterValidationError(
                    f"Vector field '{vector_field}' not found in model",
                    data=dispatch_adapt_meth(adapt_meth, items[0], adapt_kw or {}, type(items[0])),
                )

            # Validate ID field exists
            if not hasattr(items[0], id_field):
                raise AdapterValidationError(
                    f"ID field '{id_field}' not found in model",
                    data=dispatch_adapt_meth(adapt_meth, items[0], adapt_kw or {}, type(items[0])),
                )

            # Create client
            client = cls._client(url)

            # Get vector dimension
            vector = getattr(items[0], vector_field)
            cls._validate_vector_dimensions(vector)
            dim = len(vector)

            # Create or recreate collection
            try:
                client.recreate_collection(
                    collection,
                    vectors_config=qd.VectorParams(size=dim, distance="Cosine"),
                )
            except UnexpectedResponse as e:
                raise QueryError(
                    f"Failed to create Qdrant collection: {e}",
                    adapter="qdrant",
                ) from e
            except Exception as e:
                # Check for various DNS and connection-related error messages
                if (
                    "nodename nor servname provided" in str(e)
                    or "connection" in str(e).lower()
                    or "Name or service not known" in str(e)
                    or "getaddrinfo failed" in str(e)
                ):
                    raise ConnectionError(
                        f"Failed to connect to Qdrant: {e}",
                        adapter="qdrant",
                        url=url,
                    ) from e
                else:
                    raise QueryError(
                        f"Unexpected error creating Qdrant collection: {e}",
                        adapter="qdrant",
                    ) from e

            # Create points
            try:
                points = []
                for _i, item in enumerate(items):
                    vector = getattr(item, vector_field)
                    cls._validate_vector_dimensions(vector, dim)

                    # Create payload with all fields using dispatch_adapt_meth
                    # The test_qdrant_to_obj_with_custom_vector_field test expects
                    # the embedding field to be excluded, but other integration tests
                    # expect it to be included. We'll include it for now and handle
                    # the test case separately.
                    payload = dispatch_adapt_meth(adapt_meth, item, adapt_kw or {}, type(item))

                    points.append(
                        qd.PointStruct(
                            id=getattr(item, id_field),
                            vector=vector,
                            payload=payload,
                        )
                    )
            except AdapterValidationError:
                # Re-raise validation errors
                raise
            except Exception as e:
                cls._handle_error(
                    e,
                    "validation",
                    data=items,
                )

            # Upsert points
            try:
                client.upsert(collection, points)
                return {"upserted_count": len(points)}
            except UnexpectedResponse as e:
                raise QueryError(
                    f"Failed to upsert points to Qdrant: {e}",
                    adapter="qdrant",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Unexpected error upserting points to Qdrant: {e}",
                    adapter="qdrant",
                ) from e

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)

    # incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ) -> T | list[T]:
        try:
            # Validate required parameters
            if "collection" not in obj:
                raise AdapterValidationError("Missing required parameter 'collection'", data=obj)
            if "query_vector" not in obj:
                raise AdapterValidationError("Missing required parameter 'query_vector'", data=obj)

            # Validate query vector
            cls._validate_vector_dimensions(obj["query_vector"])

            # Create client
            client = cls._client(obj.get("url"))

            # Execute search
            try:
                # Set a high score threshold to ensure we get enough results
                res = client.search(
                    obj["collection"],
                    obj["query_vector"],
                    limit=obj.get("top_k", 5),
                    with_payload=True,
                    score_threshold=0.0,  # Return all results regardless of similarity
                )
            except UnexpectedResponse as e:
                if "not found" in str(e).lower():
                    raise ResourceError(
                        f"Qdrant collection not found: {e}",
                        resource=obj["collection"],
                    ) from e
                raise QueryError(
                    f"Failed to search Qdrant: {e}",
                    adapter="qdrant",
                ) from e
            except grpc.RpcError as e:
                raise ConnectionError(
                    f"Qdrant RPC error: {e}",
                    adapter="qdrant",
                    url=obj.get("url"),
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Unexpected error searching Qdrant: {e}",
                    adapter="qdrant",
                ) from e

            # Extract payloads
            docs = [r.payload for r in res]

            # Handle empty result set
            if not docs:
                if many:
                    return []
                raise ResourceError(
                    "No points found matching the query vector",
                    resource=obj["collection"],
                )

            # Convert documents to model instances using dispatch_adapt_meth
            try:
                if many:
                    return [
                        dispatch_adapt_meth(adapt_meth, d, adapt_kw or {}, subj_cls) for d in docs
                    ]
                return dispatch_adapt_meth(adapt_meth, docs[0], adapt_kw or {}, subj_cls)
            except validation_errors as e:
                cls._handle_error(
                    e,
                    "validation",
                    data=docs[0] if not many else docs,
                    errors=e.errors() if hasattr(e, "errors") else None,
                )

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)
