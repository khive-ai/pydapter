"""
AsyncMongoAdapter - uses `motor.motor_asyncio`.
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from ..async_core import AsyncAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncMongoAdapter(AsyncAdapter[T]):
    obj_key = "async_mongo"

    @classmethod
    def _client(cls, url: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(url)

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        coll = cls._client(obj["url"])[obj["db"]][obj["collection"]]
        docs = await coll.find(obj.get("filter") or {}).to_list(length=None)
        return (
            [subj_cls.model_validate(d) for d in docs]
            if many
            else subj_cls.model_validate(docs[0])
        )

    # outgoing
    @classmethod
    async def to_obj(
        cls, subj: T | Sequence[T], /, *, url, db, collection, many=True, **kw
    ):
        items = subj if isinstance(subj, Sequence) else [subj]
        payload = [i.model_dump() for i in items]
        await cls._client(url)[db][collection].insert_many(payload)
