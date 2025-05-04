"""
AsyncNeo4jAdapter – uses neo4j.AsyncGraphDatabase.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from neo4j import AsyncGraphDatabase
from pydantic import BaseModel

from ..src.pydapter.async_core import AsyncAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncNeo4jAdapter(AsyncAdapter[T]):
    obj_key = "async_neo4j"

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        driver = AsyncGraphDatabase.driver(obj["url"])
        label = obj.get("label", subj_cls.__name__)
        where = f"WHERE {obj['where']}" if "where" in obj else ""
        cypher = f"MATCH (n:`{label}`) {where} RETURN n"
        async with driver:
            async with driver.session() as s:
                rows = [r["n"]._properties async for r in s.run(cypher)]
        return (
            [subj_cls.model_validate(r) for r in rows]
            if many
            else subj_cls.model_validate(rows[0])
        )

    # outgoing
    @classmethod
    async def to_obj(
        cls, subj: T | Sequence[T], /, *, url, label=None, merge_on="id", **kw
    ):
        items = subj if isinstance(subj, Sequence) else [subj]
        label = label or items[0].__class__.__name__
        driver = AsyncGraphDatabase.driver(url)
        async with driver:
            async with driver.session() as s:
                for it in items:
                    props = it.model_dump()
                    cypher = (
                        f"MERGE (n:`{label}` {{{merge_on}: $val}}) " f"SET n += $props"
                    )
                    await s.run(cypher, val=props[merge_on], props=props)
