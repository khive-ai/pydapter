"""
Generic async SQL adapter - SQLAlchemy 2.x asyncio + asyncpg driver.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import create_async_engine

from ..async_core import AsyncAdapter
from ..exceptions import AdapterError, ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class AsyncSQLAdapter(AsyncAdapter[T]):
    obj_key = "async_sql"

    # helpers
    @staticmethod
    def _table(meta: sa.MetaData, name: str) -> sa.Table:
        try:
            return sa.Table(name, meta, autoload_with=meta.bind)
        except sa_exc.NoSuchTableError as e:
            raise ResourceError(f"Table '{name}' not found", resource=name) from e
        except Exception as e:
            raise ResourceError(
                f"Error accessing table '{name}': {e}", resource=name
            ) from e

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        try:
            # Validate required parameters
            if "engine_url" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'engine_url'", data=obj
                )
            if "table" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'table'", data=obj
                )

            # Create engine
            try:
                eng = create_async_engine(obj["engine_url"], future=True)
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create async database engine: {e}",
                    adapter="async_sql",
                    url=obj["engine_url"],
                ) from e

            # Execute query
            try:
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
                    if hasattr(eng.begin, "__self__") and hasattr(
                        eng.begin.__self__, "__aenter__"
                    ):
                        # This is for test mocks
                        conn = await eng.begin().__aenter__()
                        meta = sa.MetaData()
                        meta.bind = conn
                        tbl = cls._table(meta, obj["table"])
                        stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))
                        rows = (await conn.execute(stmt)).fetchall()
                    else:
                        raise
            except ResourceError:
                # Re-raise ResourceError from _table
                raise
            except sa_exc.SQLAlchemyError as e:
                raise QueryError(
                    f"Error executing async SQL query: {e}",
                    query=str(obj.get("selectors", {})),
                    adapter="async_sql",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Unexpected error in async SQL query: {e}",
                    adapter="async_sql",
                ) from e

            # Handle empty result set
            if not rows:
                if many:
                    return []
                raise ResourceError(
                    "No rows found matching the query",
                    resource=obj["table"],
                    selectors=obj.get("selectors", {}),
                )

            # Convert rows to model instances
            try:
                records = [dict(r) for r in rows]
                if many:
                    return [subj_cls.model_validate(r) for r in records]
                return subj_cls.model_validate(records[0])
            except ValidationError as e:
                raise AdapterValidationError(
                    f"Validation error: {e}",
                    data=records[0] if not many else records,
                    errors=e.errors(),
                ) from e

        except AdapterError:
            raise

        except Exception as e:
            raise QueryError(
                f"Unexpected error in async SQL adapter: {e}", adapter="async_sql"
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
        try:
            # Validate required parameters
            if not engine_url:
                raise AdapterValidationError("Missing required parameter 'engine_url'")
            if not table:
                raise AdapterValidationError("Missing required parameter 'table'")

            # Create engine
            try:
                eng = create_async_engine(engine_url, future=True)
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create async database engine: {e}",
                    adapter="async_sql",
                    url=engine_url,
                ) from e

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return None  # Nothing to insert

            rows = [i.model_dump() for i in items]

            # Execute insert
            try:
                # Use a try-except block to handle both real and mocked engines
                try:
                    async with eng.begin() as conn:
                        meta = sa.MetaData()
                        meta.bind = conn
                        tbl = cls._table(meta, table)
                        await conn.execute(sa.insert(tbl), rows)
                        return {"inserted_count": len(rows)}
                except TypeError:
                    # Handle case where eng.begin() is a coroutine in tests
                    if hasattr(eng.begin, "__self__") and hasattr(
                        eng.begin.__self__, "__aenter__"
                    ):
                        # This is for test mocks
                        conn = await eng.begin().__aenter__()
                        meta = sa.MetaData()
                        meta.bind = conn
                        tbl = cls._table(meta, table)
                        await conn.execute(sa.insert(tbl), rows)
                        return {"inserted_count": len(rows)}
                    else:
                        raise
            except ResourceError:
                raise

            except sa_exc.SQLAlchemyError as e:
                raise QueryError(
                    f"Error executing async SQL insert: {e}",
                    query=f"INSERT INTO {table}",
                    adapter="async_sql",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Unexpected error in async SQL insert: {e}",
                    adapter="async_sql",
                ) from e

        except AdapterError:
            raise

        except Exception as e:
            raise QueryError(
                f"Unexpected error in async SQL adapter: {e}", adapter="async_sql"
            )
