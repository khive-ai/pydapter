"""
AsyncMongoAdapter - uses `motor.motor_asyncio`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ValidationError
import pymongo
from pymongo import MongoClient
import pymongo.errors

from ..async_core import AsyncAdapter, AsyncAdapterBase
from ..core import dispatch_adapt_meth
from ..exceptions import ConnectionError, PydapterError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


__all__ = (
    "AsyncMongoAdapter",
    "MongoClient",
)


class AsyncMongoAdapter(AsyncAdapterBase, AsyncAdapter[T]):
    """
    Asynchronous MongoDB adapter for converting between Pydantic models and MongoDB documents.

    This adapter provides async methods to:
    - Query MongoDB collections asynchronously and convert documents to Pydantic models
    - Insert Pydantic models as documents into MongoDB collections asynchronously
    - Handle async MongoDB operations using Motor (async MongoDB driver)
    - Support for various async MongoDB operations (find, insert, update, delete)

    Attributes:
        adapter_key: The key identifier for this adapter type ("async_mongo")
        obj_key: Legacy key identifier (for backward compatibility)

    Example:
        ```python
        import asyncio
        from pydantic import BaseModel
        from pydapter.extras.async_mongo_ import AsyncMongoAdapter

        class User(BaseModel):
            name: str
            email: str
            age: int

        async def main():
            # Query from MongoDB
            query_config = {
                "url": "mongodb://localhost:27017",
                "database": "myapp",
                "collection": "users",
                "filter": {"age": {"$gte": 18}}
            }
            users = await AsyncMongoAdapter.from_obj(User, query_config, many=True)

            # Insert to MongoDB
            insert_config = {
                "url": "mongodb://localhost:27017",
                "database": "myapp",
                "collection": "users"
            }
            new_users = [User(name="John", email="john@example.com", age=30)]
            await AsyncMongoAdapter.to_obj(new_users, insert_config, many=True)

        asyncio.run(main())
        ```
    """

    adapter_key = "async_mongo"
    obj_key = "async_mongo"  # Backward compatibility

    @classmethod
    def _client(cls, url: str) -> AsyncIOMotorClient:
        try:
            return AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        except pymongo.errors.ConfigurationError as e:
            raise ConnectionError(
                f"Invalid MongoDB connection string: {e}",
                adapter="async_mongo",
                url=url,
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to create MongoDB client: {e}", adapter="async_mongo", url=url
            ) from e

    @classmethod
    async def _validate_connection(cls, client: AsyncIOMotorClient) -> None:
        """Validate that the MongoDB connection is working."""
        try:
            # This will raise an exception if the connection fails
            await client.admin.command("ping")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ConnectionError(
                f"MongoDB server selection timeout: {e}", adapter="async_mongo"
            ) from e
        except pymongo.errors.OperationFailure as e:
            if "auth failed" in str(e).lower():
                raise ConnectionError(
                    f"MongoDB authentication failed: {e}", adapter="async_mongo"
                ) from e
            raise QueryError(f"MongoDB operation failure: {e}", adapter="async_mongo") from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to MongoDB: {e}", adapter="async_mongo"
            ) from e

    # -------- Helper Methods --------

    @classmethod
    def _validate_params(cls, obj: dict | None = None, **kw: Any) -> None:
        """
        Validate required MongoDB connection parameters.

        Args:
            obj: Dictionary with parameters (for from_obj)
            **kw: Keyword arguments (for to_obj)

        Raises:
            AdapterValidationError: If required parameters are missing
        """
        try:
            # Check dict-based parameters (from_obj)
            if obj is not None:
                if "url" not in obj:
                    raise AdapterValidationError("Missing required parameter 'url'", data=obj)
                if "db" not in obj:
                    raise AdapterValidationError("Missing required parameter 'db'", data=obj)
                if "collection" not in obj:
                    raise AdapterValidationError(
                        "Missing required parameter 'collection'", data=obj
                    )
            # Check kwarg-based parameters (to_obj)
            else:
                if not kw.get("url"):
                    raise AdapterValidationError("Missing required parameter 'url'")
                if not kw.get("db"):
                    raise AdapterValidationError("Missing required parameter 'db'")
                if not kw.get("collection"):
                    raise AdapterValidationError("Missing required parameter 'collection'")
        except AdapterValidationError:
            raise
        except Exception as e:
            cls._handle_error(e, "validation", unexpected=True)

    @classmethod
    def _get_collection(cls, client: AsyncIOMotorClient, db: str, collection: str):
        """
        Get MongoDB collection reference.

        Args:
            client: MongoDB client instance
            db: Database name
            collection: Collection name

        Returns:
            MongoDB collection object
        """
        return client[db][collection]

    @classmethod
    def _validate_filter(cls, filter_query: Any) -> dict:
        """
        Validate and normalize filter query.

        Args:
            filter_query: Filter query to validate

        Returns:
            Normalized filter dictionary

        Raises:
            AdapterValidationError: If filter is invalid type
        """
        try:
            # Default to empty dict if None
            if filter_query is None:
                return {}

            # Validate is dict type
            if not isinstance(filter_query, dict):
                raise AdapterValidationError(
                    "Filter must be a dictionary",
                    data=filter_query,
                )

            return filter_query
        except AdapterValidationError:
            raise
        except Exception as e:
            cls._handle_error(e, "validation", unexpected=True)

    @classmethod
    async def _execute_find(
        cls, collection, filter_query: dict, url: str, db: str, coll_name: str
    ) -> list:
        """
        Execute async find query with comprehensive error handling.

        Args:
            collection: MongoDB collection object
            filter_query: Query filter dictionary
            url: MongoDB connection URL (for error context)
            db: Database name (for error context)
            coll_name: Collection name (for error context)

        Returns:
            List of documents

        Raises:
            ConnectionError: If unauthorized access
            QueryError: If query execution fails
        """
        try:
            return await collection.find(filter_query).to_list(length=None)
        except pymongo.errors.OperationFailure as e:
            if "not authorized" in str(e).lower():
                raise ConnectionError(
                    f"Not authorized to access {db}.{coll_name}: {e}",
                    adapter="async_mongo",
                    url=url,
                ) from e
            raise QueryError(
                f"MongoDB query error: {e}",
                query=filter_query,
                adapter="async_mongo",
            ) from e
        except Exception as e:
            raise QueryError(
                f"Error executing MongoDB query: {e}",
                query=filter_query,
                adapter="async_mongo",
            ) from e

    @classmethod
    def _handle_empty_result(cls, many: bool, resource: str, filter_query: dict):
        """
        Handle empty result sets consistently.

        Args:
            many: Whether processing multiple or single records
            resource: Resource identifier (e.g., "db.collection")
            filter_query: The filter used in the query

        Returns:
            Empty list if many=True

        Raises:
            ResourceError: If many=False (single record expected but not found)
        """
        if many:
            return []
        raise ResourceError(
            "No documents found matching the query",
            resource=resource,
            filter=filter_query,
        )

    @classmethod
    def _convert_documents(
        cls,
        subj_cls: type[T],
        docs: list[dict],
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...],
    ) -> T | list[T]:
        """
        Convert MongoDB documents to Pydantic models.

        Args:
            subj_cls: Target model class
            docs: List of MongoDB documents
            many: Whether processing multiple or single records
            adapt_meth: Adaptation method name or callable
            adapt_kw: Keyword arguments for adaptation method
            validation_errors: Tuple of expected validation error types

        Returns:
            Single model instance or list of model instances

        Raises:
            AdapterValidationError: If validation fails
        """
        try:
            if many:
                return [dispatch_adapt_meth(adapt_meth, d, adapt_kw, subj_cls) for d in docs]
            return dispatch_adapt_meth(adapt_meth, docs[0], adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=docs[0] if not many else docs,
                errors=e.errors() if hasattr(e, "errors") else None,
            )

    @classmethod
    def _prepare_payload(
        cls,
        subj: T | Sequence[T],
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
    ) -> list[dict] | None:
        """
        Prepare models for MongoDB insertion.

        Args:
            subj: Single model or sequence of models
            adapt_meth: Adaptation method name or callable
            adapt_kw: Keyword arguments for adaptation method

        Returns:
            List of document dictionaries, or None if empty
        """
        try:
            # Convert single item to list
            items = subj if isinstance(subj, Sequence) else [subj]

            # Return None if empty
            if not items:
                return None

            # Serialize models using adapt_meth
            return [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]
        except Exception as e:
            cls._handle_error(e, "validation", unexpected=True)

    @classmethod
    async def _execute_insert(
        cls, collection, payload: list[dict], url: str, db: str, coll_name: str
    ) -> dict:
        """
        Execute async insert_many with comprehensive error handling.

        Args:
            collection: MongoDB collection object
            payload: List of documents to insert
            url: MongoDB connection URL (for error context)
            db: Database name (for error context)
            coll_name: Collection name (for error context)

        Returns:
            Dictionary with inserted_count

        Raises:
            ConnectionError: If unauthorized access
            QueryError: If insert operation fails
        """
        try:
            result = await collection.insert_many(payload)
            return {"inserted_count": len(result.inserted_ids)}
        except pymongo.errors.BulkWriteError as e:
            raise QueryError(
                f"MongoDB bulk write error: {e}",
                adapter="async_mongo",
            ) from e
        except pymongo.errors.OperationFailure as e:
            if "not authorized" in str(e).lower():
                raise ConnectionError(
                    f"Not authorized to write to {db}.{coll_name}: {e}",
                    adapter="async_mongo",
                    url=url,
                ) from e
            raise QueryError(
                f"MongoDB operation failure: {e}",
                adapter="async_mongo",
            ) from e
        except Exception as e:
            raise QueryError(
                f"Error inserting documents into MongoDB: {e}",
                adapter="async_mongo",
            ) from e

    # -------- Protocol Methods --------

    # incoming
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ) -> T | list[T]:
        try:
            # Validate parameters
            cls._validate_params(obj)

            # Create and validate client
            client = cls._client(obj["url"])
            await cls._validate_connection(client)

            # Get collection and validate filter
            coll = cls._get_collection(client, obj["db"], obj["collection"])
            filter_query = cls._validate_filter(obj.get("filter"))

            # Execute query (await needed)
            docs = await cls._execute_find(
                coll, filter_query, obj["url"], obj["db"], obj["collection"]
            )

            # Handle empty results
            if not docs:
                return cls._handle_empty_result(
                    many, f"{obj['db']}.{obj['collection']}", filter_query
                )

            # Convert documents to models
            return cls._convert_documents(
                subj_cls, docs, many, adapt_meth, adapt_kw, validation_errors
            )

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        url: str,
        db: str,
        collection: str,
        many: bool = True,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> dict | None:
        try:
            # Validate parameters
            cls._validate_params(None, url=url, db=db, collection=collection)

            # Create and validate client
            client = cls._client(url)
            await cls._validate_connection(client)

            # Prepare payload
            payload = cls._prepare_payload(subj, adapt_meth, adapt_kw)
            if not payload:
                return None  # Nothing to insert

            # Get collection and execute insert (await needed)
            coll = cls._get_collection(client, db, collection)
            return await cls._execute_insert(coll, payload, url, db, collection)

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)
