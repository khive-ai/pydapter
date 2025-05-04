"""
MongoDB adapter (requires `pymongo`).
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

from pydantic import BaseModel
from pymongo import MongoClient

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class MongoAdapter(Adapter[T]):
    obj_key = "mongo"

    @classmethod
    def _client(cls, url: str) -> MongoClient:
        return MongoClient(url)

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        coll = cls._client(obj["url"])[obj["db"]][obj["collection"]]
        docs = list(coll.find(obj.get("filter") or {}))
        if many:
            return [subj_cls.model_validate(d) for d in docs]
        return subj_cls.model_validate(docs[0])

    # outgoing
    @classmethod
    def to_obj(cls, subj: T | Sequence[T], /, *, url, db, collection, many=True, **kw):
        items = subj if isinstance(subj, Sequence) else [subj]
        payload = [i.model_dump() for i in items]
        cls._client(url)[db][collection].insert_many(payload)
