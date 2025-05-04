"""
Generic SQL adapter using SQLAlchemy Core (requires `sqlalchemy>=2.0`).
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

import sqlalchemy as sa
from pydantic import BaseModel, ValidationError

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class SQLAdapter(Adapter[T]):
    obj_key = "sql"

    # ---- helpers
    @staticmethod
    def _table(metadata: sa.MetaData, table: str) -> sa.Table:
        try:
            return sa.Table(table, metadata, autoload_with=metadata.bind)
        except sa.exc.NoSuchTableError as e:
            raise ResourceError(f"Table '{table}' not found", resource=table) from e
        except Exception as e:
            raise ResourceError(
                f"Error accessing table '{table}': {e}", resource=table
            ) from e

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

            # Create engine and connect to database
            try:
                eng = sa.create_engine(obj["engine_url"], future=True)
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create database engine: {e}",
                    adapter="sql",
                    url=obj["engine_url"],
                ) from e

            # Create metadata and get table
            try:
                md = sa.MetaData(bind=eng)
                tbl = cls._table(md, obj["table"])
            except ResourceError:
                # Re-raise ResourceError from _table
                raise
            except Exception as e:
                raise ResourceError(
                    f"Error accessing table metadata: {e}",
                    resource=obj["table"],
                ) from e

            # Build query
            stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))

            # Execute query
            try:
                with eng.begin() as conn:
                    rows = conn.execute(stmt).fetchall()
            except Exception as e:
                raise QueryError(
                    f"Error executing query: {e}",
                    query=str(stmt),
                    adapter="sql",
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
                if many:
                    return [subj_cls.model_validate(r._mapping) for r in rows]
                return subj_cls.model_validate(rows[0]._mapping)
            except ValidationError as e:
                raise AdapterValidationError(
                    f"Validation error: {e}",
                    data=rows[0]._mapping if not many else [r._mapping for r in rows],
                    errors=e.errors(),
                ) from e

        except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(f"Unexpected error in SQL adapter: {e}", adapter="sql")

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
        try:
            # Validate required parameters
            if not engine_url:
                raise AdapterValidationError("Missing required parameter 'engine_url'")
            if not table:
                raise AdapterValidationError("Missing required parameter 'table'")

            # Create engine and connect to database
            try:
                eng = sa.create_engine(engine_url, future=True)
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create database engine: {e}",
                    adapter="sql",
                    url=engine_url,
                ) from e

            # Create metadata and get table
            try:
                md = sa.MetaData(bind=eng)
                tbl = cls._table(md, table)
            except ResourceError:
                # Re-raise ResourceError from _table
                raise
            except Exception as e:
                raise ResourceError(
                    f"Error accessing table metadata: {e}",
                    resource=table,
                ) from e

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return None  # Nothing to insert

            rows = [i.model_dump() for i in items]

            # Execute insert
            try:
                with eng.begin() as conn:
                    conn.execute(sa.insert(tbl), rows)
            except Exception as e:
                raise QueryError(
                    f"Error executing insert: {e}",
                    query=f"INSERT INTO {table}",
                    adapter="sql",
                ) from e

            return None

        except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(f"Unexpected error in SQL adapter: {e}", adapter="sql")
