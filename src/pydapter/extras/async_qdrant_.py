"""AsyncQdrantAdapter, obj_key = 'async_qdrant'"""

from __future__ import annotations

from collections.abc import Sequence

import grpc
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qd
from qdrant_client.http.exceptions import UnexpectedResponse

from ..async_core import AsyncAdapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class AsyncQdrantAdapter(AsyncAdapter[T]):
    """
    Asynchronous Qdrant vector database adapter for async vector operations.

    This adapter provides async methods to:
    - Search for similar vectors asynchronously and convert results to Pydantic models
    - Insert Pydantic models as vector points into Qdrant collections asynchronously
    - Handle async vector similarity operations and metadata filtering
    - Support for both cloud and self-hosted Qdrant instances with async operations

    Attributes:
        obj_key: The key identifier for this adapter type ("async_qdrant")

    Example:
        ```python
        import asyncio
        from pydantic import BaseModel
        from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

        class Document(BaseModel):
            id: str
            text: str
            embedding: list[float]
            category: str

        async def main():
            # Search for similar vectors
            search_config = {
                "url": "http://localhost:6333",
                "collection_name": "documents",
                "query_vector": [0.1, 0.2, 0.3, ...],  # 768-dim vector
                "limit": 10,
                "score_threshold": 0.8
            }
            similar_docs = await AsyncQdrantAdapter.from_obj(Document, search_config, many=True)

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
            await AsyncQdrantAdapter.to_obj(new_docs, insert_config, many=True)

        asyncio.run(main())
        ```
    """

    obj_key = "async_qdrant"

    @classmethod
    def _client(cls, url: str | None):
        """
        Create an async Qdrant client with proper error handling.

        Args:
            url: Qdrant server URL or None for in-memory instance

        Returns:
            AsyncQdrantClient instance

        Raises:
            ConnectionError: If connection cannot be established
        """
        try:
            return AsyncQdrantClient(url=url) if url else AsyncQdrantClient(":memory:")
        except UnexpectedResponse as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to connect to Qdrant", url=url, cause=e
            )
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Unexpected error connecting to Qdrant", url=url, cause=e
            )

    @staticmethod
    def _validate_vector_dimensions(vector, expected_dim=None):
        """Validate that the vector has the correct dimensions."""
        if not isinstance(vector, (list, tuple)) or not all(
            isinstance(x, (int, float)) for x in vector
        ):
            raise ValidationError(
                "Vector must be a list or tuple of numbers", details={"data": vector}
            )

        if expected_dim is not None and len(vector) != expected_dim:
            raise ValidationError(
                f"Vector dimension mismatch: expected {expected_dim}, got {len(vector)}",
                details={"data": vector},
            )

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        collection,
        vector_field="embedding",
        id_field="id",
        url=None,
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Validate required parameters
        if not collection:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'collection'"
            )

        # Prepare data
        items = subj if isinstance(subj, Sequence) else [subj]
        if not items:
            return None  # Nothing to insert

        # Validate vector field exists
        if not hasattr(items[0], vector_field):
            raise ValidationError.from_adapter(
                cls,
                f"Vector field '{vector_field}' not found in model",
                data=adapt_dump(items[0], adapt_meth, adapt_kw),
            )

        # Validate ID field exists
        if not hasattr(items[0], id_field):
            raise ValidationError.from_adapter(
                cls,
                f"ID field '{id_field}' not found in model",
                data=adapt_dump(items[0], adapt_meth, adapt_kw),
            )

        # Get vector dimension
        vector = getattr(items[0], vector_field)
        cls._validate_vector_dimensions(vector)
        dim = len(vector)

        # Create client
        client = cls._client(url)

        # Create or recreate collection
        try:
            await client.recreate_collection(
                collection,
                vectors_config=qd.VectorParams(size=dim, distance="Cosine"),
            )
        except UnexpectedResponse as e:
            raise QueryError.from_adapter(
                cls,
                "Failed to create Qdrant collection",
                collection_name=collection,
                cause=e,
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls,
                "Unexpected error creating Qdrant collection",
                collection_name=collection,
                cause=e,
            )

        # Create points
        try:
            points = []
            for i, item in enumerate(items):
                vector = getattr(item, vector_field)
                cls._validate_vector_dimensions(vector, dim)

                points.append(
                    qd.PointStruct(
                        id=getattr(item, id_field),
                        vector=vector,
                        payload=adapt_dump(
                            item,
                            adapt_meth,
                            {**(adapt_kw or {}), "exclude": {vector_field}},
                        ),
                    )
                )
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise ValidationError.from_adapter(
                cls, "Error creating Qdrant points", data=items, cause=e
            )

        # Upsert points
        try:
            await client.upsert(collection, points)
            return {"upserted_count": len(points)}
        except UnexpectedResponse as e:
            raise QueryError.from_adapter(
                cls, "Failed to upsert points to Qdrant", cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Unexpected error upserting points to Qdrant", cause=e
            )

    # incoming
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        if "collection" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'collection'", data=obj
            )
        if "query_vector" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'query_vector'", data=obj
            )

        # Validate query vector & Create client
        cls._validate_vector_dimensions(obj["query_vector"])
        client = cls._client(obj.get("url"))

        # Execute search
        try:
            res = await client.search(
                obj["collection"],
                obj["query_vector"],
                limit=obj.get("top_k", 5),
                with_payload=True,
            )
        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                raise ResourceError.from_adapter(
                    cls,
                    "Qdrant collection not found",
                    resource=obj["collection"],
                    cause=e,
                )
            raise QueryError.from_adapter(
                cls,
                "Failed to search Qdrant",
                query_vector=obj["query_vector"],
                cause=e,
            )
        except grpc.RpcError as e:
            raise ConnectionError.from_adapter(
                cls, "Qdrant RPC error", url=obj.get("url"), cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls,
                "Unexpected error searching Qdrant",
                query_vector=obj["query_vector"],
                cause=e,
            )

        # Extract payloads
        docs = [r.payload for r in res]

        # Handle empty result set
        if not docs:
            if many:
                return []
            raise ResourceError.from_adapter(
                cls,
                "No points found matching the query vector",
                resource=obj["collection"],
            )

        # Convert documents to model instances
        try:
            if many:
                return [adapt_from(subj_cls, d, adapt_meth, adapt_kw) for d in docs]
            return adapt_from(subj_cls, docs[0], adapt_meth, adapt_kw)
        except ValidationError as e:
            raise ValidationError.from_adapter(
                cls,
                "Validation error converting to model",
                data=docs[0] if not many else docs,
                cause=e,
            )
