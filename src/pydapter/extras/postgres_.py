"""
PostgresAdapter – thin preset over SQLAdapter (pgvector-ready if you add vec column).
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from pydantic import BaseModel

from .sql_ import SQLAdapter

T = TypeVar("T", bound=BaseModel)


class PostgresAdapter(SQLAdapter[T]):  # type: ignore[type-arg]
    obj_key = "postgres"
    DEFAULT = "postgresql+psycopg://user:pass@localhost/db"

    @classmethod
    def from_obj(cls, subj_cls, obj: dict, /, **kw):
        obj.setdefault("engine_url", cls.DEFAULT)
        return super().from_obj(subj_cls, obj, **kw)

    @classmethod
    def to_obj(cls, subj, /, **kw):
        kw.setdefault("engine_url", cls.DEFAULT)
        return super().to_obj(subj, **kw)
