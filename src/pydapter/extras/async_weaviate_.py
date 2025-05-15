"""
AsyncWeaviateAdapter - Asynchronous adapter for Weaviate vector database.

This adapter provides asynchronous access to Weaviate using aiohttp for REST API calls.
It follows the AsyncAdapter protocol and provides comprehensive error handling and
resource management.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any, Dict, List, TypeVar, Union

import aiohttp
from pydantic import BaseModel, ValidationError

from ..async_core import AsyncAdapter
from ..exceptions import ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class AsyncWeaviateAdapter(AsyncAdapter[T]):
    """
    Asynchronous adapter for Weaviate vector database.

    This adapter provides methods to convert between Pydantic models and Weaviate objects,
    with full support for asynchronous operations.
    """

    obj_key = "async_weav"

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        class_name: str,
        url: str = "http://localhost:8080",
        vector_field: str = "embedding",
        **kw,
    ) -> dict[str, Any]:
        """
        Convert from Pydantic models to Weaviate objects asynchronously.

        Args:
            subj: Model instance or sequence of model instances
            class_name: Weaviate class name
            url: Weaviate server URL (defaults to http://localhost:8080)
            vector_field: Field containing vector data (defaults to "embedding")
            **kw: Additional keyword arguments

        Returns:
            dict: Operation result with count of added objects

        Raises:
            AdapterValidationError: If required parameters are missing or invalid
            ConnectionError: If connection to Weaviate fails
            QueryError: If query execution fails
        """
        try:
            # Validate required parameters
            if not class_name:
                raise AdapterValidationError("Missing required parameter 'class_name'")
            if not url:
                raise AdapterValidationError("Missing required parameter 'url'")

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"added_count": 0}  # Nothing to insert

            # Create collection if it doesn't exist
            collection_payload = {
                "class": class_name,
                "vectorizer": "none",  # Skip vectorization, we provide vectors
                "properties": [],  # No predefined properties
            }

            added_count = 0
            try:
                async with aiohttp.ClientSession() as session:
                    # Create schema class if it doesn't exist
                    try:
                        # First check if collection exists
                        async with session.get(f"{url}/v1/schema/{class_name}") as resp:
                            if resp.status == 404:
                                # Collection doesn't exist, create it
                                async with session.post(
                                    f"{url}/v1/schema", json=collection_payload
                                ) as schema_resp:
                                    if schema_resp.status not in (200, 201):
                                        schema_error = await schema_resp.text()
                                        raise QueryError(
                                            f"Failed to create collection: {schema_error}",
                                            adapter="async_weav",
                                        )
                    except aiohttp.ClientError as e:
                        raise ConnectionError(
                            f"Failed to connect to Weaviate: {e}",
                            adapter="async_weav",
                            url=url,
                        ) from e

                    # Add objects
                    for it in items:
                        # Validate vector field exists
                        if not hasattr(it, vector_field):
                            raise AdapterValidationError(
                                f"Vector field '{vector_field}' not found in model",
                                data=it.model_dump(),
                            )

                        # Get vector data
                        vector = getattr(it, vector_field)
                        if not isinstance(vector, list):
                            raise AdapterValidationError(
                                f"Vector field '{vector_field}' must be a list of floats",
                                data=it.model_dump(),
                            )

                        # Prepare payload - exclude id and vector_field from properties
                        properties = it.model_dump(exclude={vector_field, "id"})

                        # Generate a UUID based on the model's ID if available
                        obj_uuid = None
                        if hasattr(it, "id"):
                            # Create a deterministic UUID from the model ID
                            # This ensures the same model ID always maps to the same UUID
                            namespace = uuid.UUID(
                                "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
                            )  # UUID namespace
                            obj_uuid = str(uuid.uuid5(namespace, f"{it.id}"))

                        payload = {
                            "class": class_name,
                            "properties": properties,
                            "vector": vector,
                        }

                        # Add UUID if available
                        if obj_uuid:
                            payload["id"] = obj_uuid

                        # Add object
                        try:
                            async with session.post(
                                f"{url}/v1/objects", json=payload
                            ) as resp:
                                if resp.status not in (200, 201):
                                    error_text = await resp.text()
                                    raise QueryError(
                                        f"Failed to add object to Weaviate: {error_text}",
                                        adapter="async_weav",
                                    )
                                added_count += 1
                        except aiohttp.ClientError as e:
                            raise ConnectionError(
                                f"Failed to connect to Weaviate: {e}",
                                adapter="async_weav",
                                url=url,
                            ) from e

                return {"added_count": added_count}

            except (ConnectionError, QueryError, AdapterValidationError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Wrap other exceptions
                raise QueryError(
                    f"Error in Weaviate operation: {e}",
                    adapter="async_weav",
                ) from e

        except (ConnectionError, QueryError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(
                f"Unexpected error in async Weaviate adapter: {e}", adapter="async_weav"
            ) from e

    # incoming
    @classmethod
    async def from_obj(
        cls, subj_cls: type[T], obj: dict[str, Any], /, *, many: bool = True, **kw
    ) -> T | list[T]:
        """
        Convert from Weaviate objects to Pydantic models asynchronously.

        Args:
            subj_cls: Target model class
            obj: Dictionary with query parameters
            many: Whether to return multiple results
            **kw: Additional keyword arguments

        Required parameters in obj:
            class_name: Weaviate class name
            query_vector: Vector to search for similar objects

        Optional parameters in obj:
            url: Weaviate server URL (defaults to http://localhost:8080)
            top_k: Maximum number of results to return (defaults to 5)

        Returns:
            T | list[T]: Single model instance or list of model instances

        Raises:
            AdapterValidationError: If required parameters are missing
            ConnectionError: If connection to Weaviate fails
            QueryError: If query execution fails
            ResourceError: If no matching objects are found
        """
        try:
            # Validate required parameters
            if "class_name" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'class_name'", data=obj
                )
            if "query_vector" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'query_vector'", data=obj
                )

            # Prepare GraphQL query
            url = obj.get("url", "http://localhost:8080")
            top_k = obj.get("top_k", 5)
            class_name = obj["class_name"]

            # Updated GraphQL query for Weaviate v4
            # Use the updated GraphQL query format for Weaviate v4
            query = {
                "query": """
                {
                  Get {
                    %s(
                      nearVector: {
                        vector: %s
                        distance: 0.7
                      }
                      limit: %d
                    ) {
                      _additional { id }
                      ... on %s { * }
                    }
                  }
                }
                """
                % (class_name, json.dumps(obj["query_vector"]), top_k, class_name)
            }

            try:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(
                            f"{url}/v1/graphql", json=query
                        ) as resp:
                            if resp.status != 200:
                                error_text = await resp.text()
                                raise QueryError(
                                    f"Failed to execute Weaviate query: {error_text}",
                                    adapter="async_weav",
                                )
                            data = await resp.json()
                    except aiohttp.ClientError as e:
                        raise ConnectionError(
                            f"Failed to connect to Weaviate: {e}",
                            adapter="async_weav",
                            url=url,
                        ) from e

                # Extract data
                # Handle both JSON response formats
                if (
                    "data" in data
                    and "Get" in data["data"]
                    and class_name in data["data"]["Get"]
                ):
                    # Standard GraphQL response format
                    recs = data["data"]["Get"][class_name]
                elif "errors" in data:
                    # GraphQL error response
                    error_msg = data.get("errors", [{}])[0].get(
                        "message", "Unknown GraphQL error"
                    )
                    raise QueryError(
                        f"GraphQL error: {error_msg}",
                        adapter="async_weav",
                    )
                else:
                    # No data found
                    if many:
                        return []
                    raise ResourceError(
                        "No objects found matching the query",
                        resource=class_name,
                    )
                if not recs:
                    if many:
                        return []
                    raise ResourceError(
                        "No objects found matching the query",
                        resource=class_name,
                    )

                # Convert to model instances
                try:
                    if many:
                        return [subj_cls.model_validate(r) for r in recs]
                    return subj_cls.model_validate(recs[0])
                except ValidationError as e:
                    raise AdapterValidationError(
                        f"Validation error: {e}",
                        data=recs[0] if not many else recs,
                        errors=e.errors(),
                    ) from e

            except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Wrap other exceptions
                raise QueryError(
                    f"Error in Weaviate query: {e}",
                    adapter="async_weav",
                ) from e

        except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(
                f"Unexpected error in async Weaviate adapter: {e}", adapter="async_weav"
            ) from e
