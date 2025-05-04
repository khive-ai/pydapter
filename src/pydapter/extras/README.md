## Template for AsyncAdapter

```python
class AsyncMongoAdapter(AsyncAdapter[T]):
    obj_key = "async_mongo"

    @classmethod
    async def from_obj(...):
        client = motor.motor_asyncio.AsyncIOMotorClient(url)
        docs = await client[db][coll].find(flt).to_list(length=None)
        ...

    @classmethod
    async def to_obj(...):
        ...
        await client[db][coll].insert_many(payload)
```
