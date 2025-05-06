"""
MongoDB adapter (requires `pymongo`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

import pymongo
import pymongo.errors
from pydantic import BaseModel, ValidationError
from pymongo import MongoClient

from ..core import Adapter
from ..exceptions import AdapterError, ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


__all__ = (
    "MongoAdapter",
    "MongoClient",
)


class MongoAdapter(Adapter[T]):
    obj_key = "mongo"

    @classmethod
    def _client(cls, url: str) -> pymongo.MongoClient:
        try:
            return pymongo.MongoClient(url, serverSelectionTimeoutMS=5000)
        except pymongo.errors.ConfigurationError as e:
            raise ConnectionError(
                f"Invalid MongoDB connection string: {e}", adapter="mongo", url=url
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to create MongoDB client: {e}", adapter="mongo", url=url
            ) from e

    @classmethod
    def _validate_connection(cls, client: pymongo.MongoClient) -> None:
        """Validate that the MongoDB connection is working."""
        try:
            # This will raise an exception if the connection fails
            client.admin.command("ping")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ConnectionError(
                f"MongoDB server selection timeout: {e}", adapter="mongo"
            ) from e
        except pymongo.errors.OperationFailure as e:
            if "auth failed" in str(e).lower():
                raise ConnectionError(
                    f"MongoDB authentication failed: {e}", adapter="mongo"
                ) from e
            raise QueryError(f"MongoDB operation failure: {e}", adapter="mongo") from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to MongoDB: {e}", adapter="mongo"
            ) from e

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        try:
            # Validate required parameters
            if "url" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'url'", data=obj
                )
            if "db" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'db'", data=obj
                )
            if "collection" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'collection'", data=obj
                )

            # Create client and validate connection
            client = cls._client(obj["url"])
            cls._validate_connection(client)

            # Get collection and execute query
            try:
                coll = client[obj["db"]][obj["collection"]]
                filter_query = obj.get("filter") or {}

                # Validate filter query if provided
                if filter_query and not isinstance(filter_query, dict):
                    raise AdapterValidationError(
                        "Filter must be a dictionary",
                        data=filter_query,
                    )

                docs = list(coll.find(filter_query))
            except pymongo.errors.OperationFailure as e:
                if "not authorized" in str(e).lower():
                    raise ConnectionError(
                        f"Not authorized to access {obj['db']}.{obj['collection']}: {e}",
                        adapter="mongo",
                        url=obj["url"],
                    ) from e
                raise QueryError(
                    f"MongoDB query error: {e}",
                    query=filter_query,
                    adapter="mongo",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Error executing MongoDB query: {e}",
                    query=filter_query,
                    adapter="mongo",
                ) from e

            # Handle empty result set
            if not docs:
                if many:
                    return []
                raise ResourceError(
                    "No documents found matching the query",
                    resource=f"{obj['db']}.{obj['collection']}",
                    filter=filter_query,
                )

            # Convert documents to model instances
            try:
                if many:
                    return [subj_cls.model_validate(d) for d in docs]
                return subj_cls.model_validate(docs[0])
            except ValidationError as e:
                raise AdapterValidationError(
                    f"Validation error: {e}",
                    data=docs[0] if not many else docs,
                    errors=e.errors(),
                ) from e

        except AdapterError:
            raise

        except Exception as e:
            raise QueryError(
                f"Unexpected error in MongoDB adapter: {e}", adapter="mongo"
            )

    # outgoing
    @classmethod
    def to_obj(cls, subj: T | Sequence[T], /, *, url, db, collection, many=True, **kw):
        try:
            # Validate required parameters
            if not url:
                raise AdapterValidationError("Missing required parameter 'url'")
            if not db:
                raise AdapterValidationError("Missing required parameter 'db'")
            if not collection:
                raise AdapterValidationError("Missing required parameter 'collection'")

            # Create client and validate connection
            client = cls._client(url)
            cls._validate_connection(client)

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return None  # Nothing to insert

            payload = [i.model_dump() for i in items]

            # Execute insert
            try:
                result = client[db][collection].insert_many(payload)
                return {"inserted_count": result.inserted_ids}
            except pymongo.errors.BulkWriteError as e:
                raise QueryError(
                    f"MongoDB bulk write error: {e}",
                    adapter="mongo",
                ) from e
            except pymongo.errors.OperationFailure as e:
                if "not authorized" in str(e).lower():
                    raise ConnectionError(
                        f"Not authorized to write to {db}.{collection}: {e}",
                        adapter="mongo",
                        url=url,
                    ) from e
                raise QueryError(
                    f"MongoDB operation failure: {e}",
                    adapter="mongo",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Error inserting documents into MongoDB: {e}",
                    adapter="mongo",
                ) from e

        except AdapterError:
            raise

        except Exception as e:
            # Wrap other exceptions
            raise QueryError(
                f"Unexpected error in MongoDB adapter: {e}", adapter="mongo"
            )
