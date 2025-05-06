"""
Weaviate adapter (requires `weaviate-client`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

import weaviate
from pydantic import BaseModel

from ..src.pydapter.core import Adapter

T = TypeVar("T", bound=BaseModel)


class WeaviateAdapter(Adapter[T]):
    obj_key = "weav"

    @staticmethod
    def _client(url: str | None):
        return weaviate.Client(url) if url else weaviate.Client("http://localhost:8080")

    # outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        class_name,
        vector_field="embedding",
        url=None,
        **kw,
    ):
        client = cls._client(url)
        client.schema.get_or_create(class_name, vectorizer_config={"skip": True})
        items = subj if isinstance(subj, Sequence) else [subj]
        with client.batch as batch:
            for it in items:
                batch.add_data_object(
                    it.model_dump(exclude={vector_field}),
                    class_name=class_name,
                    vector=getattr(it, vector_field),
                )

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        client = cls._client(obj.get("url"))
        res = (
            client.query.get(obj["class_name"], ["*"])
            .with_near_vector({"vector": obj["query_vector"]})
            .with_limit(obj.get("top_k", 5))
            .do()
        )
        data = res["data"]["Get"][obj["class_name"]]
        return (
            [subj_cls.model_validate(r) for r in data]
            if many
            else subj_cls.model_validate(data[0])
        )
