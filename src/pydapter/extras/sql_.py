"""
Generic SQL adapter using SQLAlchemy Core (requires `sqlalchemy>=2.0`).
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

import sqlalchemy as sa
from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class SQLAdapter(Adapter[T]):
    obj_key = "sql"

    # ---- helpers
    @staticmethod
    def _table(metadata: sa.MetaData, table: str) -> sa.Table:
        return sa.Table(table, metadata, autoload_with=metadata.bind)

    # ---- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        **kw,
    ):
        eng = sa.create_engine(obj["engine_url"], future=True)
        md = sa.MetaData(bind=eng)
        tbl = cls._table(md, obj["table"])
        stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))
        with eng.begin() as conn:
            rows = conn.execute(stmt).fetchall()
        if many:
            return [subj_cls.model_validate(r._mapping) for r in rows]
        return subj_cls.model_validate(rows[0]._mapping)

    # ---- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        engine_url: str,
        table: str,
        many=True,
        **kw,
    ) -> None:
        eng = sa.create_engine(engine_url, future=True)
        md = sa.MetaData(bind=eng)
        tbl = cls._table(md, table)
        items = subj if isinstance(subj, Sequence) else [subj]
        rows = [i.model_dump() for i in items]
        with eng.begin() as conn:
            conn.execute(sa.insert(tbl), rows)
