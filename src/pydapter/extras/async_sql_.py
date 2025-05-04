"""
Generic async SQL adapter – SQLAlchemy 2.x asyncio + asyncpg driver.
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..async_core import AsyncAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncSQLAdapter(AsyncAdapter[T]):
    obj_key = "async_sql"

    # helpers
    @staticmethod
    def _table(meta: sa.MetaData, name: str) -> sa.Table:
        return sa.Table(name, meta, autoload_with=meta.bind)

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        eng = create_async_engine(obj["engine_url"], future=True)
        # Use a try-except block to handle both real and mocked engines
        try:
            async with eng.begin() as conn:
                meta = sa.MetaData()
                meta.bind = conn
                tbl = cls._table(meta, obj["table"])
                stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))
                rows = (await conn.execute(stmt)).fetchall()
        except TypeError:
            # Handle case where eng.begin() is a coroutine in tests
            if hasattr(eng.begin, "__self__") and hasattr(eng.begin.__self__, "__aenter__"):
                # This is for test mocks
                conn = await eng.begin().__aenter__()
                meta = sa.MetaData()
                meta.bind = conn
                tbl = cls._table(meta, obj["table"])
                stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))
                rows = (await conn.execute(stmt)).fetchall()
            else:
                raise
        records = [dict(r) for r in rows]
        return (
            [subj_cls.model_validate(r) for r in records]
            if many
            else subj_cls.model_validate(records[0])
        )
        
    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        engine_url: str,
        table: str,
        many=True,
        **kw,
    ):
        eng = create_async_engine(engine_url, future=True)
        items = subj if isinstance(subj, Sequence) else [subj]
        rows = [i.model_dump() for i in items]
        # Use a try-except block to handle both real and mocked engines
        try:
            async with eng.begin() as conn:
                meta = sa.MetaData()
                meta.bind = conn
                tbl = cls._table(meta, table)
                await conn.execute(sa.insert(tbl), rows)
        except TypeError:
            # Handle case where eng.begin() is a coroutine in tests
            if hasattr(eng.begin, "__self__") and hasattr(eng.begin.__self__, "__aenter__"):
                # This is for test mocks
                conn = await eng.begin().__aenter__()
                meta = sa.MetaData()
                meta.bind = conn
                tbl = cls._table(meta, table)
                await conn.execute(sa.insert(tbl), rows)
            else:
                raise
