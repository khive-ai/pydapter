"""
Neo4j adapter (requires `neo4j`).
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from neo4j import GraphDatabase
from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class Neo4jAdapter(Adapter[T]):
    obj_key = "neo4j"

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        driver = GraphDatabase.driver(obj["url"])
        label = obj.get("label", subj_cls.__name__)
        where = f"WHERE {obj['where']}" if "where" in obj else ""
        cypher = f"MATCH (n:`{label}`) {where} RETURN n"
        with driver.session() as s:
            rows = [r["n"]._properties for r in s.run(cypher)]
        if many:
            return [subj_cls.model_validate(r) for r in rows]
        return subj_cls.model_validate(rows[0])

    # outgoing
    @classmethod
    def to_obj(cls, subj: T | Sequence[T], /, *, url, label=None, merge_on="id", **kw):
        items = subj if isinstance(subj, Sequence) else [subj]
        label = label or items[0].__class__.__name__
        driver = GraphDatabase.driver(url)
        with driver.session() as s:
            for it in items:
                props = it.model_dump()
                cypher = f"MERGE (n:`{label}` {{{merge_on}: $val}}) SET n += $props"
                s.run(cypher, val=props[merge_on], props=props)
