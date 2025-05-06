# pydapter extras

This directory contains additional adapters for various data sources and
formats.

## Available Adapters

- **Database Adapters**: SQL, PostgreSQL, MongoDB, Neo4j, Qdrant
- **Async Database Adapters**: AsyncSQL, AsyncPostgres, AsyncMongo, AsyncQdrant
- **Other Formats**: Excel, Pandas

## Error Handling

All adapters in this directory implement robust error handling using the
pydapter exception hierarchy:

- `ConnectionError`: Raised when connection to a data source fails
- `QueryError`: Raised when a query to a data source fails
- `ResourceError`: Raised when a resource (table, collection, etc.) cannot be
  accessed
- `ValidationError`: Raised when data validation fails
- `ConfigurationError`: Raised when adapter configuration is invalid

See the [Error Handling Documentation](../../../docs/error_handling.md) for more
details.

## Template for AsyncAdapter

```python
class AsyncMongoAdapter(AsyncAdapter[T]):
    obj_key = "async_mongo"

    @classmethod
    async def from_obj(cls, subj_cls, obj, /, **kw):
        try:
            # Validate required parameters
            if "url" not in obj:
                raise ValidationError("Missing required parameter 'url'")
            if "db" not in obj:
                raise ValidationError("Missing required parameter 'db'")
            if "collection" not in obj:
                raise ValidationError("Missing required parameter 'collection'")

            # Connect to database
            client = motor.motor_asyncio.AsyncIOMotorClient(obj["url"])

            # Execute query
            docs = await client[obj["db"]][obj["collection"]].find(obj.get("filter", {})).to_list(length=None)

            # Handle empty result set
            if not docs and not kw.get("many", True):
                raise ResourceError(
                    "No documents found matching the query",
                    resource=f"{obj['db']}.{obj['collection']}",
                    filter=obj.get("filter", {})
                )

            # Process results
            return [subj_cls(**doc) for doc in docs] if kw.get("many", True) else subj_cls(**docs[0])

        except motor.errors.ConnectionFailure as e:
            raise ConnectionError(
                f"MongoDB connection failed: {e}",
                adapter="async_mongo",
                url=obj.get("url")
            )
        except motor.errors.OperationFailure as e:
            raise QueryError(
                f"MongoDB query error: {e}",
                query=obj.get("filter"),
                adapter="async_mongo"
            )

    @classmethod
    async def to_obj(cls, subj, /, **kw):
        # Similar error handling for to_obj method
        ...
```
