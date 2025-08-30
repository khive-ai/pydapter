"""
Generic async SQL adapter - SQLAlchemy 2.x asyncio + asyncpg driver.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, TypedDict, TypeVar

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql import text
from typing_extensions import NotRequired, Required

from ..async_core import AsyncAdapter
from ..exceptions import (
    AdapterError,
    ConnectionError,
    QueryError,
    ResourceError,
    ValidationError,
)

T = TypeVar("T", bound=BaseModel)


class SQLReadConfig(TypedDict):
    """Configuration for SQL read operations (from_obj)."""

    # Connection (exactly one required)
    dsn: NotRequired[str]  # Database connection string
    engine_url: NotRequired[str]  # Legacy: Database connection string
    engine: NotRequired[AsyncEngine]  # Pre-existing SQLAlchemy engine

    # Operation type
    operation: NotRequired[Literal["select", "delete", "raw_sql"]]  # Default: "select"

    # For select/delete operations
    table: NotRequired[str]  # Table name
    selectors: NotRequired[dict[str, Any]]  # WHERE conditions
    limit: NotRequired[int]  # LIMIT clause
    offset: NotRequired[int]  # OFFSET clause
    order_by: NotRequired[str]  # ORDER BY clause

    # For raw_sql operation
    sql: NotRequired[str]  # Raw SQL statement
    params: NotRequired[dict[str, Any]]  # SQL parameters for safe binding
    fetch_results: NotRequired[bool]  # Whether to fetch results (default: True)


class SQLWriteConfig(TypedDict):
    """Configuration for SQL write operations (to_obj as **kwargs)."""

    # Connection (exactly one required)
    dsn: NotRequired[str]  # Database connection string
    engine_url: NotRequired[str]  # Legacy: Database connection string
    engine: NotRequired[AsyncEngine]  # Pre-existing SQLAlchemy engine

    # Required
    table: Required[str]  # Table name

    # Operation type
    operation: NotRequired[Literal["insert", "update", "upsert"]]  # Default: "insert"

    # For update operations
    where: NotRequired[dict[str, Any]]  # WHERE conditions for UPDATE

    # For upsert operations
    conflict_columns: NotRequired[list[str]]  # Columns that define conflicts
    update_columns: NotRequired[list[str]]  # Columns to update on conflict


class AsyncSQLAdapter(AsyncAdapter[T]):
    """
    Asynchronous SQL adapter using SQLAlchemy 2.x asyncio for database operations.

    This adapter provides async methods to:
    - Execute SQL queries asynchronously and convert results to Pydantic models
    - Insert Pydantic models as rows into database tables asynchronously
    - Update, delete, and upsert operations through configuration
    - Execute raw SQL with parameterized queries
    - Support for various async SQL databases through SQLAlchemy
    - Handle connection pooling and async context management

    Attributes:
        obj_key: The key identifier for this adapter type ("async_sql")

    Configuration Examples:
        ```python
        from pydantic import BaseModel
        from pydapter.extras.async_sql_ import AsyncSQLAdapter, SQLReadConfig, SQLWriteConfig

        class User(BaseModel):
            id: int
            name: str
            email: str

        # Using TypedDict for type hints (recommended for IDE support)
        config: SQLReadConfig = {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "table": "users",
            "selectors": {"active": True},
            "limit": 10
        }
        users = await AsyncSQLAdapter.from_obj(User, config, many=True)

        # Or inline dict (same as before)
        users = await AsyncSQLAdapter.from_obj(User, {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "table": "users",
            "selectors": {"active": True},
            "limit": 10
        }, many=True)

        # DELETE via config
        result = await AsyncSQLAdapter.from_obj(User, {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "operation": "delete",
            "table": "users",
            "selectors": {"id": 123}
        })

        # Raw SQL execution
        result = await AsyncSQLAdapter.from_obj(User, {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "operation": "raw_sql",
            "sql": "SELECT * FROM users WHERE created_at > :since",
            "params": {"since": "2024-01-01"}
        }, many=True)

        # INSERT (default operation)
        result = await AsyncSQLAdapter.to_obj(
            new_user,
            dsn="postgresql+asyncpg://user:pass@localhost/db",
            table="users"
        )

        # UPDATE via config
        result = await AsyncSQLAdapter.to_obj(
            updated_user,
            dsn="postgresql+asyncpg://user:pass@localhost/db",
            table="users",
            operation="update",
            where={"id": 123}
        )

        # UPSERT via config
        result = await AsyncSQLAdapter.to_obj(
            user_data,
            dsn="postgresql+asyncpg://user:pass@localhost/db",
            table="users",
            operation="upsert",
            conflict_columns=["email"]
        )
        ```
    """

    obj_key = "async_sql"

    @staticmethod
    def _table(meta: sa.MetaData, name: str, conn=None) -> sa.Table:
        """
        Helper method to get a SQLAlchemy Table object for async operations.

        Args:
            meta: SQLAlchemy MetaData instance
            name: Name of the table to load
            conn: Optional connection for reflection

        Returns:
            SQLAlchemy Table object

        Raises:
            ResourceError: If table is not found or cannot be accessed
        """
        try:
            # For async, we can't autoload - just create table reference
            # The actual schema validation happens at query execution
            return sa.Table(name, meta)
        except Exception as e:
            raise ResourceError(
                f"Error accessing table '{name}': {e}", resource=name
            ) from e

    # incoming
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: SQLReadConfig | dict,  # TypedDict for IDE support
        /,
        *,
        many=True,
        adapt_meth: str = "model_validate",
        **kw,
    ):
        try:
            # Get operation type (default: "select" for backward compatibility)
            operation = obj.get("operation", "select").lower()

            # Validate only one engine parameter is provided
            engine_params = sum(["engine" in obj, "dsn" in obj, "engine_url" in obj])

            if engine_params == 0:
                raise ValidationError(
                    "Missing required parameter: one of 'engine', 'dsn', or 'engine_url'",
                    data=obj,
                )
            elif engine_params > 1:
                raise ValidationError(
                    "Multiple engine parameters provided. Use only one of: 'engine', 'dsn', or 'engine_url'",
                    data=obj,
                )

            # Get engine - either passed directly or create from DSN
            if "engine" in obj:
                eng = obj["engine"]  # Use provided engine
            elif "dsn" in obj:
                # Create new engine from DSN
                try:
                    eng = create_async_engine(obj["dsn"], future=True)
                except Exception as e:
                    raise ConnectionError(
                        f"Failed to create async database engine: {e}",
                        adapter="async_sql",
                        url=obj["dsn"],
                    ) from e
            else:  # engine_url
                # Create new engine from URL
                try:
                    eng = create_async_engine(obj["engine_url"], future=True)
                except Exception as e:
                    raise ConnectionError(
                        f"Failed to create async database engine: {e}",
                        adapter="async_sql",
                        url=obj["engine_url"],
                    ) from e

            # Handle different operations
            if operation == "select":
                # Standard SELECT operation (existing behavior)
                if "table" not in obj:
                    raise ValidationError(
                        "Missing required parameter 'table'", data=obj
                    )

                try:
                    async with eng.begin() as conn:
                        # Use run_sync for table reflection
                        def sync_select(sync_conn):
                            meta = sa.MetaData()
                            tbl = sa.Table(obj["table"], meta, autoload_with=sync_conn)

                            # Build query with optional selectors
                            stmt = sa.select(tbl)
                            if "selectors" in obj and obj["selectors"]:
                                for key, value in obj["selectors"].items():
                                    stmt = stmt.where(getattr(tbl.c, key) == value)

                            # Add limit/offset if specified
                            if "limit" in obj:
                                stmt = stmt.limit(obj["limit"])
                            if "offset" in obj:
                                stmt = stmt.offset(obj["offset"])
                            # Add order_by if specified
                            if "order_by" in obj:
                                stmt = stmt.order_by(text(obj["order_by"]))

                            result = sync_conn.execute(stmt)
                            # Convert Row objects to dicts
                            return [dict(row._mapping) for row in result.fetchall()]

                        rows = await conn.run_sync(sync_select)

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing async SQL query: {e}",
                        query=str(obj.get("selectors", {})),
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

                # Convert rows to model instances (rows are already dicts from run_sync)
                try:
                    if many:
                        return [getattr(subj_cls, adapt_meth)(r) for r in rows]
                    return getattr(subj_cls, adapt_meth)(rows[0])
                except PydanticValidationError as e:
                    raise ValidationError(
                        f"Validation error: {e}", data=rows[0] if not many else rows
                    ) from e

            elif operation == "delete":
                # DELETE operation
                if "table" not in obj:
                    raise ValidationError(
                        "Missing required parameter 'table' for delete operation",
                        data=obj,
                    )

                try:
                    async with eng.begin() as conn:
                        # Use run_sync for table reflection
                        def sync_delete(sync_conn):
                            meta = sa.MetaData()
                            tbl = sa.Table(obj["table"], meta, autoload_with=sync_conn)

                            # Build DELETE statement with selectors
                            stmt = sa.delete(tbl)
                            if "selectors" in obj and obj["selectors"]:
                                for key, value in obj["selectors"].items():
                                    stmt = stmt.where(getattr(tbl.c, key) == value)
                            else:
                                raise ValidationError(
                                    "DELETE operation requires 'selectors' to prevent accidental full table deletion",
                                    data=obj,
                                )

                            result = sync_conn.execute(stmt)
                            return result.rowcount

                        deleted = await conn.run_sync(sync_delete)
                        return {"deleted_count": deleted}

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing async SQL delete: {e}",
                        adapter="async_sql",
                    ) from e

            elif operation == "raw_sql":
                # Raw SQL execution
                if "sql" not in obj:
                    raise ValidationError(
                        "Missing required parameter 'sql' for raw_sql operation",
                        data=obj,
                    )

                try:
                    async with eng.begin() as conn:
                        # Use SQLAlchemy text() for parameterized queries
                        stmt = text(obj["sql"])
                        params = obj.get("params", {})
                        result = await conn.execute(stmt, params)

                        # Handle result based on fetch_results flag and SQL type
                        fetch_results = obj.get("fetch_results", True)
                        if fetch_results and result.returns_rows:
                            rows = result.fetchall()
                            if not rows:
                                return [] if many else None

                            # Try to convert to Pydantic models if possible
                            try:
                                # Convert Row objects to dicts
                                records = [
                                    (
                                        dict(r._mapping)
                                        if hasattr(r, "_mapping")
                                        else dict(r)
                                    )
                                    for r in rows
                                ]
                                if (
                                    subj_cls is not dict
                                ):  # Only convert if not using generic dict
                                    if many:
                                        return [
                                            getattr(subj_cls, adapt_meth)(r)
                                            for r in records
                                        ]
                                    return getattr(subj_cls, adapt_meth)(records[0])
                                else:
                                    return records if many else records[0]
                            except (PydanticValidationError, TypeError):
                                # If conversion fails, return raw dicts
                                records = [
                                    (
                                        dict(r._mapping)
                                        if hasattr(r, "_mapping")
                                        else dict(r)
                                    )
                                    for r in rows
                                ]
                                return records if many else records[0]
                        else:
                            # For DDL, procedures, or when fetch_results=False
                            return {
                                "affected_rows": (
                                    result.rowcount if result.rowcount != -1 else 0
                                )
                            }

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing raw SQL: {e}",
                        adapter="async_sql",
                    ) from e

            else:
                raise ValidationError(
                    f"Unsupported operation '{operation}' for from_obj. "
                    f"Supported operations: select, delete, raw_sql",
                    data=obj,
                )

        except AdapterError:
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in async SQL adapter: {e}", adapter="async_sql"
            ) from e

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_dump",
        **kw,
    ):
        try:
            # Get operation type (default: "insert" for backward compatibility)
            operation = kw.get("operation", "insert").lower()

            # Validate required parameters
            if "table" not in kw:
                raise ValidationError("Missing required parameter 'table'")

            table = kw["table"]

            # Validate only one engine parameter is provided
            engine_params = sum(["engine" in kw, "dsn" in kw, "engine_url" in kw])

            if engine_params == 0:
                raise ValidationError(
                    "Missing required parameter: one of 'engine', 'dsn', or 'engine_url'"
                )
            elif engine_params > 1:
                raise ValidationError(
                    "Multiple engine parameters provided. Use only one of: 'engine', 'dsn', or 'engine_url'"
                )

            # Get engine - either passed directly or create from DSN
            if "engine" in kw:
                eng = kw["engine"]  # Use provided engine
            elif "dsn" in kw:
                # Create new engine from DSN
                try:
                    eng = create_async_engine(kw["dsn"], future=True)
                except Exception as e:
                    raise ConnectionError(
                        f"Failed to create async database engine: {e}",
                        adapter="async_sql",
                        url=kw["dsn"],
                    ) from e
            else:  # engine_url
                # Create new engine from URL
                try:
                    eng = create_async_engine(kw["engine_url"], future=True)
                except Exception as e:
                    raise ConnectionError(
                        f"Failed to create async database engine: {e}",
                        adapter="async_sql",
                        url=kw["engine_url"],
                    ) from e

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"affected_count": 0}

            # Handle different operations
            if operation == "insert":
                # Standard INSERT operation (existing behavior)
                rows = [getattr(i, adapt_meth)() for i in items]

                try:
                    async with eng.begin() as conn:
                        # Use run_sync to handle table reflection properly
                        def sync_insert(sync_conn):
                            meta = sa.MetaData()
                            tbl = sa.Table(table, meta, autoload_with=sync_conn)
                            # Filter out None values from rows to let DB handle defaults
                            clean_rows = [
                                {k: v for k, v in row.items() if v is not None}
                                for row in rows
                            ]
                            sync_conn.execute(sa.insert(tbl), clean_rows)
                            return len(clean_rows)

                        count = await conn.run_sync(sync_insert)
                        return {"inserted_count": count}

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing async SQL insert: {e}",
                        query=f"INSERT INTO {table}",
                        adapter="async_sql",
                    ) from e

            elif operation == "update":
                # UPDATE operation
                if "where" not in kw:
                    raise ValidationError("UPDATE operation requires 'where' parameter")

                where_conditions = kw["where"]
                update_data = [getattr(i, adapt_meth)() for i in items]

                try:
                    async with eng.begin() as conn:
                        # Use run_sync for table reflection
                        def sync_update(sync_conn):
                            meta = sa.MetaData()
                            tbl = sa.Table(table, meta, autoload_with=sync_conn)

                            total_updated = 0
                            for data in update_data:
                                # Filter out None values and don't update primary keys
                                clean_data = {
                                    k: v
                                    for k, v in data.items()
                                    if v is not None and k != "id"
                                }
                                if not clean_data:
                                    continue

                                # Build WHERE clause from conditions
                                stmt = sa.update(tbl)
                                for key, value in where_conditions.items():
                                    stmt = stmt.where(getattr(tbl.c, key) == value)

                                # Apply updates
                                stmt = stmt.values(**clean_data)
                                result = sync_conn.execute(stmt)
                                total_updated += result.rowcount

                            return total_updated

                        count = await conn.run_sync(sync_update)
                        return {"updated_count": count}

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing async SQL update: {e}",
                        adapter="async_sql",
                    ) from e

            elif operation == "upsert":
                # UPSERT operation (basic implementation, PostgreSQL adapter has better version)
                if "conflict_columns" not in kw:
                    raise ValidationError(
                        "UPSERT operation requires 'conflict_columns' parameter"
                    )

                # For basic SQL adapter, implement as INSERT with error handling
                # PostgreSQL adapter will override with proper ON CONFLICT
                rows = [getattr(i, adapt_meth)() for i in items]
                conflict_columns = kw["conflict_columns"]

                try:
                    async with eng.begin() as conn:
                        # Use run_sync for table reflection
                        def sync_upsert(sync_conn):
                            meta = sa.MetaData()
                            tbl = sa.Table(table, meta, autoload_with=sync_conn)

                            inserted_count = 0
                            updated_count = 0

                            for row in rows:
                                # Clean the row data - remove None values
                                clean_row = {
                                    k: v for k, v in row.items() if v is not None
                                }

                                # Check if record exists
                                select_stmt = sa.select(tbl)
                                for col in conflict_columns:
                                    if col in clean_row:
                                        select_stmt = select_stmt.where(
                                            getattr(tbl.c, col) == clean_row[col]
                                        )

                                existing = sync_conn.execute(select_stmt).fetchone()

                                if existing:
                                    # Update existing record - don't update primary keys
                                    update_data = {
                                        k: v for k, v in clean_row.items() if k != "id"
                                    }
                                    if update_data:
                                        update_stmt = sa.update(tbl)
                                        for col in conflict_columns:
                                            if col in clean_row:
                                                update_stmt = update_stmt.where(
                                                    getattr(tbl.c, col)
                                                    == clean_row[col]
                                                )
                                        update_stmt = update_stmt.values(**update_data)
                                        sync_conn.execute(update_stmt)
                                    updated_count += 1
                                else:
                                    # Insert new record
                                    insert_stmt = sa.insert(tbl).values(**clean_row)
                                    sync_conn.execute(insert_stmt)
                                    inserted_count += 1

                            return {
                                "inserted_count": inserted_count,
                                "updated_count": updated_count,
                                "total_count": inserted_count + updated_count,
                            }

                        return await conn.run_sync(sync_upsert)

                except sa_exc.SQLAlchemyError as e:
                    raise QueryError(
                        f"Error executing async SQL upsert: {e}",
                        adapter="async_sql",
                    ) from e

            else:
                raise ValidationError(
                    f"Unsupported operation '{operation}' for to_obj. "
                    f"Supported operations: insert, update, upsert"
                )

        except AdapterError:
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in async SQL adapter: {e}", adapter="async_sql"
            ) from e
