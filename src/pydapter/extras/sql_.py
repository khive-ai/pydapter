"""
Generic SQL adapter using SQLAlchemy Core (requires `sqlalchemy>=2.0`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
import sqlalchemy as sa
from sqlalchemy import exc as sq_exc
from sqlalchemy.dialects import postgresql

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class SQLAdapter(AdapterBase, Adapter[T]):
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

    adapter_key = "sql"
    obj_key = "sql"  # Backward compatibility

    # Declarative exception handling
    connection_errors = (
        sq_exc.OperationalError,
        sq_exc.DatabaseError,
        sq_exc.InterfaceError,
    )
    query_errors = (
        sq_exc.StatementError,
        sq_exc.DataError,
        sq_exc.IntegrityError,
        sq_exc.ProgrammingError,
    )

    # -------- Helper Methods --------

    @classmethod
    def _create_engine(cls, engine_url: str) -> sa.Engine:
        """Create SQLAlchemy engine with error handling."""
        try:
            return sa.create_engine(engine_url, future=True)
        except cls.connection_errors as e:
            from ..exceptions import ConnectionError

            raise ConnectionError(
                f"Failed to create database engine: {e}",
                adapter=cls.adapter_key,
                url=engine_url,
            ) from e
        except Exception as e:
            from ..exceptions import ConnectionError

            raise ConnectionError(
                f"Failed to create database engine: {e}",
                adapter=cls.adapter_key,
                url=engine_url,
            ) from e

    @classmethod
    def _reflect_metadata(cls, engine: sa.Engine, table_name: str) -> tuple[sa.MetaData, sa.Table]:
        """Reflect metadata and get table with error handling."""
        try:
            md = sa.MetaData()
            md.reflect(bind=engine)
            tbl = cls._table(md, table_name, engine=engine)
            return md, tbl
        except ResourceError:
            raise  # Re-raise ResourceError from _table
        except Exception as e:
            cls._handle_error(e, "resource", resource=table_name)

    @classmethod
    def _table(cls, metadata: sa.MetaData, table: str, engine=None) -> sa.Table:
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
            cls._handle_error(e, "resource", resource=table)
        except Exception as e:
            cls._handle_error(e, "resource", resource=table)

    @classmethod
    def _execute_query(cls, engine: sa.Engine, stmt: Any) -> list:
        """Execute query and fetch results with error handling."""
        try:
            with engine.begin() as conn:
                return conn.execute(stmt).fetchall()
        except cls.query_errors as e:
            cls._handle_error(e, "query", query=str(stmt))
        except Exception as e:
            cls._handle_error(e, "query", query=str(stmt))

    @classmethod
    def _validate_rows(
        cls,
        rows: list,
        subj_cls: type[T],
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...],
    ) -> T | list[T]:
        """Convert database rows to model instances with validation."""
        try:
            if many:
                return [
                    dispatch_adapt_meth(adapt_meth, r._mapping, adapt_kw, subj_cls) for r in rows
                ]
            return dispatch_adapt_meth(adapt_meth, rows[0]._mapping, adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=rows[0]._mapping if not many else [r._mapping for r in rows],
                errors=e.errors(),
            )

    @classmethod
    def _serialize_models(
        cls,
        items: list[T],
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
    ) -> list[dict]:
        """Convert model instances to database rows."""
        return [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]

    @classmethod
    def _execute_upsert(
        cls,
        engine: sa.Engine,
        tbl: sa.Table,
        rows: list[dict],
    ) -> int:
        """Execute insert or upsert operation with error handling."""
        try:
            with engine.begin() as conn:
                pk_columns = [c.name for c in tbl.primary_key.columns]

                if not pk_columns:
                    # If no primary key, just insert
                    conn.execute(sa.insert(tbl), rows)
                else:
                    # For PostgreSQL, use ON CONFLICT DO UPDATE
                    for row in rows:
                        update_values = {k: v for k, v in row.items() if k not in pk_columns}
                        if not update_values:
                            stmt = sa.insert(tbl).values(**row)
                        else:
                            stmt = postgresql.insert(tbl).values(**row)
                            stmt = stmt.on_conflict_do_update(
                                index_elements=pk_columns, set_=update_values
                            )
                        conn.execute(stmt)

            return len(rows)
        except cls.query_errors as e:
            cls._handle_error(e, "query", query=f"UPSERT INTO {tbl.name}")
        except Exception as e:
            cls._handle_error(e, "query", query=f"UPSERT INTO {tbl.name}")

    # ---- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ):
        try:
            # Validate required parameters
            if "engine_url" not in obj:
                raise AdapterValidationError("Missing required parameter 'engine_url'", data=obj)
            if "table" not in obj:
                raise AdapterValidationError("Missing required parameter 'table'", data=obj)

            # Create engine using helper
            eng = cls._create_engine(obj["engine_url"])

            # Reflect metadata and get table using helper
            md, tbl = cls._reflect_metadata(eng, obj["table"])

            # Build query
            stmt = sa.select(tbl).filter_by(**obj.get("selectors", {}))

            # Execute query using helper
            rows = cls._execute_query(eng, stmt)

            # Handle empty result set
            if not rows:
                if many:
                    return []
                raise ResourceError(
                    "No rows found matching the query",
                    resource=obj["table"],
                    selectors=obj.get("selectors", {}),
                )

            # Validate rows using helper
            return cls._validate_rows(rows, subj_cls, many, adapt_meth, adapt_kw, validation_errors)

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)

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
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> dict[str, Any]:
        try:
            # Validate required parameters
            if not engine_url:
                raise AdapterValidationError("Missing required parameter 'engine_url'")
            if not table:
                raise AdapterValidationError("Missing required parameter 'table'")

            # Create engine using helper
            eng = cls._create_engine(engine_url)

            # Reflect metadata and get table using helper
            md, tbl = cls._reflect_metadata(eng, table)

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"success": True, "count": 0}

            # Serialize models using helper
            rows = cls._serialize_models(items, adapt_meth, adapt_kw)

            # Execute upsert using helper
            count = cls._execute_upsert(eng, tbl, rows)

            return {"success": True, "count": count}

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "query", unexpected=True)
