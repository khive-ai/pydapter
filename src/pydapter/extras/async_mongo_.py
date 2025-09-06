"""AsyncMongoAdapter, obj_key = 'async_mongo'"""

from __future__ import annotations

from collections.abc import Sequence

import pymongo
import pymongo.errors
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from ..async_core import AsyncAdapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from

__all__ = (
    "AsyncMongoAdapter",
    "MongoClient",
)


class AsyncMongoAdapter(AsyncAdapter[T]):
    """
    Asynchronous MongoDB adapter for converting between Pydantic models and MongoDB documents.

    This adapter provides async methods to:
    - Query MongoDB collections asynchronously and convert documents to Pydantic models
    - Insert Pydantic models as documents into MongoDB collections asynchronously
    - Handle async MongoDB operations using Motor (async MongoDB driver)
    - Support for various async MongoDB operations (find, insert, update, delete)

    Attributes:
        obj_key: The key identifier for this adapter type ("async_mongo")

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

    obj_key = "async_mongo"

    @classmethod
    def _client(cls, url: str) -> AsyncIOMotorClient:
        try:
            return AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        except pymongo.errors.ConfigurationError as e:
            raise ConnectionError.from_adapter(
                cls, "Invalid MongoDB connection string", url=url, cause=e
            )
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to create MongoDB client", url=url, cause=e
            )

    @classmethod
    async def _validate_connection(cls, client: AsyncIOMotorClient) -> None:
        """Validate that the MongoDB connection is working."""
        try:
            # This will raise an exception if the connection fails
            await client.admin.command("ping")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ConnectionError.from_adapter(
                cls, "MongoDB server selection timeout", cause=e
            )
        except pymongo.errors.OperationFailure as e:
            if "auth failed" in str(e).lower():
                raise ConnectionError.from_adapter(
                    cls, "MongoDB authentication failed", cause=e
                )
            raise QueryError.from_adapter(cls, "MongoDB operation failure", cause=e)
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to connect to MongoDB", cause=e
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
        # Validate required parameters
        if "url" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'url'", data=obj
            )
        if "db" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'db'", data=obj
            )
        if "collection" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'collection'", data=obj
            )

        # Create client and validate connection
        client = cls._client(obj["url"])
        await cls._validate_connection(client)

        # Get collection and execute query
        try:
            coll = client[obj["db"]][obj["collection"]]
            filter_query = obj.get("filter") or {}

            # Validate filter query if provided
            if filter_query and not isinstance(filter_query, dict):
                raise ValidationError.from_adapter(
                    cls, "Filter must be a dictionary", data=filter_query
                )

            docs = await coll.find(filter_query).to_list(length=None)
        except pymongo.errors.OperationFailure as e:
            if "not authorized" in str(e).lower():
                raise ConnectionError.from_adapter(
                    cls,
                    f"Not authorized to access {obj['db']}.{obj['collection']}",
                    url=obj["url"],
                    cause=e,
                )
            raise QueryError.from_adapter(
                cls, "MongoDB query error", query=filter_query, cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Error executing MongoDB query", query=filter_query, cause=e
            )

        # Handle empty result set
        if not docs:
            if many:
                return []
            raise ResourceError.from_adapter(
                cls,
                "No documents found matching the query",
                resource=f"{obj['db']}.{obj['collection']}",
                filter=filter_query,
            )

        # Convert documents to model instances
        try:
            if many:
                return [adapt_from(subj_cls, d, adapt_meth, adapt_kw) for d in docs]
            return adapt_from(subj_cls, docs[0], adapt_meth, adapt_kw)
        except Exception as e:
            raise ValidationError.from_adapter(
                cls,
                "Data conversion failed",
                data=docs[0] if not many else docs,
                adapt_method=adapt_meth,
                cause=e,
            )

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        url,
        db,
        collection,
        many=True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Validate required parameters
        if not url:
            raise ValidationError.from_adapter(cls, "Missing required parameter 'url'")
        if not db:
            raise ValidationError.from_adapter(cls, "Missing required parameter 'db'")
        if not collection:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'collection'"
            )

        # Create client and validate connection
        client = cls._client(url)
        await cls._validate_connection(client)

        # Prepare data
        items = subj if isinstance(subj, Sequence) else [subj]
        if not items:
            return None  # Nothing to insert

        payload = [adapt_dump(i, adapt_meth, adapt_kw) for i in items]

        # Execute insert
        try:
            result = await client[db][collection].insert_many(payload)
            return {"inserted_count": len(result.inserted_ids)}
        except pymongo.errors.BulkWriteError as e:
            raise QueryError.from_adapter(cls, "MongoDB bulk write error", cause=e)
        except pymongo.errors.OperationFailure as e:
            if "not authorized" in str(e).lower():
                raise ConnectionError.from_adapter(
                    cls,
                    f"Not authorized to write to {db}.{collection}",
                    url=url,
                    cause=e,
                )
            raise QueryError.from_adapter(cls, "MongoDB operation failure", cause=e)
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Error inserting documents into MongoDB", cause=e
            )
