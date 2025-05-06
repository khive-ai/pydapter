"""
AsyncWeaviateAdapter - minimal REST wrapper via aiohttp.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import TypeVar

import aiohttp
from pydantic import BaseModel

from ..src.pydapter.async_core import AsyncAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncWeaviateAdapter(AsyncAdapter[T]):
    obj_key = "async_weav"

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        url="http://localhost:8080",
        class_name,
        vector_field="embedding",
        many=True,
        **kw,
    ):
        items = subj if isinstance(subj, Sequence) else [subj]
        async with aiohttp.ClientSession() as sess:
            for i in items:
                payload = {
                    "class": class_name,
                    "properties": i.model_dump(exclude={vector_field}),
                    "vector": getattr(i, vector_field),
                }
                async with sess.post(f"{url}/v1/objects", json=payload):
                    pass  # ignore response for brevity

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        query = {
            "query": """
            {
              Get {
                %s(nearVector: {vector: %s}, limit: %d) {
                  _additional { id }
                  ... on %s { * }
                }
              }
            }
            """
            % (
                obj["class_name"],
                json.dumps(obj["query_vector"]),
                obj.get("top_k", 5),
                obj["class_name"],
            )
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                f"{obj.get('url', 'http://localhost:8080')}/v1/graphql", json=query
            ) as resp:
                data = await resp.json()
        recs = data["data"]["Get"][obj["class_name"]]
        return (
            [subj_cls.model_validate(r) for r in recs]
            if many
            else subj_cls.model_validate(recs[0])
        )
