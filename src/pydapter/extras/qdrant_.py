"""
Qdrant vector-store adapter (requires `qdrant-client`).
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qd

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class QdrantAdapter(Adapter[T]):
    obj_key = "qdrant"

    # helper
    @staticmethod
    def _client(url: str | None):
        return QdrantClient(url=url) if url else QdrantClient(":memory:")

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
        **kw,
    ) -> None:
        items = subj if isinstance(subj, Sequence) else [subj]
        client = cls._client(url)
        dim = len(getattr(items[0], vector_field))
        client.recreate_collection(
            collection, vectors_config=qd.VectorParams(size=dim, distance="Cosine")
        )
        points = [
            qd.PointStruct(
                id=getattr(i, id_field),
                vector=getattr(i, vector_field),
                payload=i.model_dump(exclude={vector_field}),
            )
            for i in items
        ]
        client.upsert(collection, points)

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        client = cls._client(obj.get("url"))
        res = client.search(
            obj["collection"],
            obj["query_vector"],
            limit=obj.get("top_k", 5),
            with_payload=True,
        )
        docs = [r.payload for r in res]
        return (
            [subj_cls.model_validate(d) for d in docs]
            if many
            else subj_cls.model_validate(docs[0])
        )
