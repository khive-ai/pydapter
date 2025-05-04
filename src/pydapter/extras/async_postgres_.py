"""
AsyncPostgresAdapter – presets AsyncSQLAdapter for PostgreSQL/pgvector.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from pydantic import BaseModel

from ..async_core import AsyncAdapter
from .async_sql_ import AsyncSQLAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncPostgresAdapter(AsyncSQLAdapter[T]):  # type: ignore[type-arg]
    obj_key = "async_pg"
    DEFAULT = "postgresql+asyncpg://test:test@localhost/test"

    @classmethod
    async def from_obj(cls, subj_cls, obj: dict, /, **kw):
        # Use the provided DSN if available, otherwise use the default
        engine_url = kw.get("dsn", cls.DEFAULT)
        if "dsn" in kw:
            # Convert the PostgreSQL URL to SQLAlchemy format
            if not engine_url.startswith("postgresql+asyncpg://"):
                engine_url = engine_url.replace("postgresql://", "postgresql+asyncpg://")
        obj.setdefault("engine_url", engine_url)
        return await super().from_obj(subj_cls, obj, **kw)

    @classmethod
    async def to_obj(cls, subj, /, **kw):
        # Use the provided DSN if available, otherwise use the default
        engine_url = kw.get("dsn", cls.DEFAULT)
        if "dsn" in kw:
            # Convert the PostgreSQL URL to SQLAlchemy format
            if not engine_url.startswith("postgresql+asyncpg://"):
                engine_url = engine_url.replace("postgresql://", "postgresql+asyncpg://")
        kw.setdefault("engine_url", engine_url)
        await super().to_obj(subj, **kw)
