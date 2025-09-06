"""
Generic SQL adapter using SQLAlchemy Core (requires `sqlalchemy>=2.0`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy import exc as sq_exc
from sqlalchemy.dialects import postgresql

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class SQLAdapter(Adapter[T]):
    """
    Generic SQL adapter using SQLAlchemy Core for database operations.

    This adapter provides methods to:
    - Execute SQL queries and convert results to Pydantic models
    - Insert Pydantic models as rows into database tables
    - Support for various SQL databases through SQLAlchemy
    - Handle both raw SQL and table-based operations

    Attributes:
        obj_key: The key identifier for this adapter type ("sql")

    Example:
        ```python
        import sqlalchemy as sa
        from pydantic import BaseModel
        from pydapter.extras.sql_ import SQLAdapter

        class User(BaseModel):
            id: int
            name: str
            email: str

        # Setup database connection
        engine = sa.create_engine("sqlite:///example.db")
        metadata = sa.MetaData()

        # Query from database
        query = "SELECT id, name, email FROM users WHERE active = true"
        users = SQLAdapter.from_obj(
            User,
            query,
            many=True,
            engine=engine
        )

        # Insert to database
        new_users = [User(id=1, name="John", email="john@example.com")]
        SQLAdapter.to_obj(
            new_users,
            many=True,
            table="users",
            metadata=metadata
        )
        ```
    """

    obj_key = "sql"

    @staticmethod
    def _table(metadata: sa.MetaData, table: str, engine=None) -> sa.Table:
        """
        Helper method to get a SQLAlchemy Table object with autoloading.

        Args:
            metadata: SQLAlchemy MetaData instance
            table: Name of the table to load
            engine: Optional SQLAlchemy engine for autoloading

        Returns:
            SQLAlchemy Table object

        Raises:
            ResourceError: If table is not found or cannot be accessed
        """
        try:
            # Use engine if provided, otherwise use metadata.bind
            autoload_with = engine if engine is not None else metadata.bind  # type: ignore
            return sa.Table(table, metadata, autoload_with=autoload_with)
        except sq_exc.NoSuchTableError as e:
            raise ResourceError.from_adapter(
                cls, f"Table '{table}' not found", resource=table, cause=e
            )
        except Exception as e:
            raise ResourceError.from_adapter(
                cls, f"Error accessing table '{table}'", resource=table, cause=e
            )

    # ---- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Validate required parameters
        if "engine_url" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'engine_url'", data=obj
            )
        if "table" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'table'", data=obj
            )

        # Create engine and connect to database
        try:
            eng = sa.create_engine(obj["engine_url"], future=True)
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to create database engine", url=obj["engine_url"], cause=e
            )

        # Create metadata and get table
        try:
            md = sa.MetaData()
            md.reflect(bind=eng)
            tbl = cls._table(md, obj["table"], engine=eng)
        except Exception as e:
            # Check if this is a connection-related error
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in [
                    "authentication",
                    "connection",
                    "refused",
                    "timeout",
                    "password",
                    "auth",
                    "access denied",
                    "login",
                ]
            ):
                raise ConnectionError.from_adapter(
                    cls,
                    "Connection failed during metadata reflection",
                    url=obj["engine_url"],
                    cause=e,
                )
            raise ResourceError.from_adapter(
                cls, "Error accessing table metadata", resource=obj["table"], cause=e
            )

        # Build query
        stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))

        # Execute query
        try:
            with eng.begin() as conn:
                rows = conn.execute(stmt).fetchall()
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Error executing query", query=str(stmt), cause=e
            )

        # Handle empty result set
        if not rows:
            if many:
                return []
            raise ResourceError.from_adapter(
                cls,
                "No rows found matching the query",
                resource=obj["table"],
                selectors=obj.get("selectors", {}),
            )

        # Convert rows to model instances
        try:
            if many:
                return [
                    adapt_from(subj_cls, r._mapping, adapt_meth, adapt_kw) for r in rows
                ]
            return adapt_from(subj_cls, rows[0]._mapping, adapt_meth, adapt_kw)
        except Exception as e:
            raise ValidationError.from_adapter(
                cls,
                "Data conversion failed",
                data=(rows[0]._mapping if not many else [r._mapping for r in rows]),
                adapt_method=adapt_meth,
                cause=e,
            )

    # ---- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        engine_url: str,
        table: str,
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> dict[str, Any]:
        # Validate required parameters
        if not engine_url:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'engine_url'"
            )
        if not table:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'table'"
            )

        # Create engine and connect to database
        try:
            eng = sa.create_engine(engine_url, future=True)
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to create database engine", url=engine_url, cause=e
            )

        # Create metadata and get table
        try:
            md = sa.MetaData()
            md.reflect(bind=eng)
            tbl = cls._table(md, table, engine=eng)
        except Exception as e:
            # Check if this is a connection-related error
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in [
                    "authentication",
                    "connection",
                    "refused",
                    "timeout",
                    "password",
                    "auth",
                    "access denied",
                    "login",
                ]
            ):
                raise ConnectionError.from_adapter(
                    cls,
                    "Connection failed during metadata reflection",
                    url=engine_url,
                    cause=e,
                )
            raise ResourceError.from_adapter(
                cls, "Error accessing table metadata", resource=table, cause=e
            )

        # Prepare data
        items = subj if isinstance(subj, Sequence) else [subj]
        if not items:
            return {"success": True, "count": 0}  # Nothing to insert

        rows = [adapt_dump(i, adapt_meth, adapt_kw) for i in items]

        # Execute insert or update (upsert)
        try:
            with eng.begin() as conn:
                # Get primary key columns
                pk_columns = [c.name for c in tbl.primary_key.columns]

                if not pk_columns:
                    # If no primary key, just insert
                    conn.execute(sa.insert(tbl), rows)
                else:
                    # For PostgreSQL, use ON CONFLICT DO UPDATE
                    for row in rows:
                        # Build the values to update (excluding primary key columns)
                        update_values = {
                            k: v for k, v in row.items() if k not in pk_columns
                        }
                        if not update_values:
                            # If only primary key columns, just try to insert
                            stmt = sa.insert(tbl).values(**row)
                        else:
                            # Otherwise, do an upsert
                            stmt = postgresql.insert(tbl).values(**row)
                            stmt = stmt.on_conflict_do_update(
                                index_elements=pk_columns, set_=update_values
                            )
                        conn.execute(stmt)
        except Exception as e:
            raise QueryError.from_adapter(
                cls,
                "Error executing insert/update",
                query=f"UPSERT INTO {table}",
                cause=e,
            )

        # Return a success indicator instead of None
        return {"success": True, "count": len(rows)}
