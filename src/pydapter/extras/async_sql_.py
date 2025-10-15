"""
Generic async SQL adapter - SQLAlchemy 2.x asyncio + asyncpg driver.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import sys
from typing import Any, Literal, TypeVar

# Python 3.10 compatibility: NotRequired, Required, TypedDict
if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required, TypedDict
else:
    from typing import NotRequired, Required, TypedDict

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.sql import text

from ..async_core import AsyncAdapter, AsyncAdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class SQLReadConfig(TypedDict):
    """Configuration for SQL read operations (from_obj)."""

    # Connection (exactly one required)
    dsn: NotRequired[str]  # Database connection string
    engine_url: NotRequired[str]  # Legacy: Database connection string
    engine: NotRequired[AsyncEngine]  # Pre-existing SQLAlchemy engine

    # Operation type
    operation: NotRequired[Literal["select", "delete", "raw_sql"]]  # Default: "select"

    # For select/delete operations (table required for these)
    table: NotRequired[str]  # Table name (NOT required for raw_sql)
    selectors: NotRequired[dict[str, Any]]  # WHERE conditions
    limit: NotRequired[int]  # LIMIT clause
    offset: NotRequired[int]  # OFFSET clause
    order_by: NotRequired[str]  # ORDER BY clause

    # For raw_sql operation (table NOT required)
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


class AsyncSQLAdapter(AsyncAdapterBase, AsyncAdapter[T]):
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
        adapter_key: The key identifier for this adapter type ("async_sql")
        obj_key: Legacy key identifier (backward compatibility)

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

        # Raw SQL execution (note: table parameter NOT required)
        result = await AsyncSQLAdapter.from_obj(User, {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "operation": "raw_sql",
            "sql": "SELECT * FROM users WHERE created_at > :since",
            "params": {"since": "2024-01-01"}
        }, many=True)

        # Or with dict for flexible results (no model validation)
        result = await AsyncSQLAdapter.from_obj(dict, {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "operation": "raw_sql",
            "sql": "SELECT * FROM users ORDER BY created_at DESC LIMIT :limit",
            "params": {"limit": 10}
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

    adapter_key = "async_sql"
    obj_key = "async_sql"  # Backward compatibility

    # Declarative exception handling
    connection_errors = (
        sa_exc.OperationalError,
        sa_exc.DatabaseError,
        sa_exc.InterfaceError,
    )
    query_errors = (
        sa_exc.SQLAlchemyError,
        sa_exc.StatementError,
        sa_exc.DataError,
        sa_exc.IntegrityError,
        sa_exc.ProgrammingError,
    )

    # -------- Helper Methods --------

    @classmethod
    async def _create_engine(cls, config: dict) -> AsyncEngine:
        """
        Create async engine from config with validation and error handling.

        Args:
            config: Configuration dict with one of 'engine', 'dsn', or 'engine_url'

        Returns:
            AsyncEngine instance

        Raises:
            ValidationError: If no engine parameter or multiple engine parameters
            ConnectionError: If engine creation fails
        """
        # Validate only one engine parameter is provided
        engine_params = sum(["engine" in config, "dsn" in config, "engine_url" in config])

        if engine_params == 0:
            cls._handle_error(
                ValueError("Missing required parameter: one of 'engine', 'dsn', or 'engine_url'"),
                "validation",
                data=config,
            )
        elif engine_params > 1:
            cls._handle_error(
                ValueError("Multiple engine parameters provided"),
                "validation",
                data=config,
            )

        # Return existing engine or create new
        if "engine" in config:
            return config["engine"]

        dsn = config.get("dsn") or config.get("engine_url")
        try:
            return create_async_engine(dsn, future=True)
        except cls.connection_errors as e:
            cls._handle_error(e, "connection", url=dsn)
        except Exception as e:
            # Catch all other engine creation errors (e.g., NoSuchModuleError for invalid dialects)
            cls._handle_error(e, "connection", url=dsn)

    @classmethod
    async def _execute_select(
        cls,
        eng: AsyncEngine,
        config: dict,
    ) -> list[dict]:
        """
        Execute SELECT operation with run_sync pattern.

        Args:
            eng: AsyncEngine instance
            config: Configuration dict with table, selectors, limit, offset, order_by

        Returns:
            List of row dicts

        Raises:
            ValidationError: If table parameter missing
            QueryError: If query execution fails
        """
        if "table" not in config:
            cls._handle_error(
                ValueError("Missing required parameter 'table'"),
                "validation",
                data=config,
            )

        try:
            async with eng.begin() as conn:
                # Use run_sync for table reflection
                def sync_select(sync_conn):
                    meta = sa.MetaData()
                    tbl = sa.Table(config["table"], meta, autoload_with=sync_conn)

                    # Build query with optional selectors
                    stmt = sa.select(tbl)
                    if "selectors" in config and config["selectors"]:
                        for key, value in config["selectors"].items():
                            stmt = stmt.where(getattr(tbl.c, key) == value)

                    # Add limit/offset if specified
                    if "limit" in config:
                        stmt = stmt.limit(config["limit"])
                    if "offset" in config:
                        stmt = stmt.offset(config["offset"])
                    # Add order_by if specified
                    if "order_by" in config:
                        stmt = stmt.order_by(text(config["order_by"]))

                    result = sync_conn.execute(stmt)
                    # Convert Row objects to dicts
                    return [dict(row._mapping) for row in result.fetchall()]

                return await conn.run_sync(sync_select)

        except cls.query_errors as e:
            cls._handle_error(
                e,
                "query",
                query=str(config.get("selectors", {})),
            )

    @classmethod
    async def _execute_delete(
        cls,
        eng: AsyncEngine,
        config: dict,
    ) -> dict:
        """
        Execute DELETE operation with run_sync pattern.

        Args:
            eng: AsyncEngine instance
            config: Configuration dict with table and selectors

        Returns:
            Dict with deleted_count

        Raises:
            ValidationError: If table or selectors missing
            QueryError: If delete execution fails
        """
        if "table" not in config:
            cls._handle_error(
                ValueError("Missing required parameter 'table' for delete operation"),
                "validation",
                data=config,
            )

        try:
            async with eng.begin() as conn:
                # Use run_sync for table reflection
                def sync_delete(sync_conn):
                    meta = sa.MetaData()
                    tbl = sa.Table(config["table"], meta, autoload_with=sync_conn)

                    # Build DELETE statement with selectors
                    stmt = sa.delete(tbl)
                    if "selectors" in config and config["selectors"]:
                        for key, value in config["selectors"].items():
                            stmt = stmt.where(getattr(tbl.c, key) == value)
                    else:
                        raise AdapterValidationError(
                            "DELETE operation requires 'selectors' to prevent accidental full table deletion",
                            data=config,
                        )

                    result = sync_conn.execute(stmt)
                    return result.rowcount

                deleted = await conn.run_sync(sync_delete)
                return {"deleted_count": deleted}

        except cls.query_errors as e:
            cls._handle_error(e, "query")

    @classmethod
    async def _execute_raw_sql(
        cls,
        eng: AsyncEngine,
        config: dict,
    ) -> Any:
        """
        Execute RAW SQL operation without run_sync.

        Args:
            eng: AsyncEngine instance
            config: Configuration dict with sql, params, fetch_results

        Returns:
            Query results or affected rows dict

        Raises:
            ValidationError: If sql parameter missing
            QueryError: If SQL execution fails
        """
        if "sql" not in config:
            cls._handle_error(
                ValueError("Missing required parameter 'sql' for raw_sql operation"),
                "validation",
                data=config,
            )

        try:
            async with eng.begin() as conn:
                # Use SQLAlchemy text() for parameterized queries
                stmt = text(config["sql"])
                params = config.get("params", {})
                result = await conn.execute(stmt, params)

                # Handle result based on fetch_results flag and SQL type
                fetch_results = config.get("fetch_results", True)
                if fetch_results and result.returns_rows:
                    rows = result.fetchall()
                    if not rows:
                        return []

                    # Convert Row objects to dicts
                    return [(dict(r._mapping) if hasattr(r, "_mapping") else dict(r)) for r in rows]
                else:
                    # For DDL, procedures, or when fetch_results=False
                    return {"affected_rows": (result.rowcount if result.rowcount != -1 else 0)}

        except cls.query_errors as e:
            cls._handle_error(e, "query")

    @classmethod
    async def _execute_insert(
        cls,
        eng: AsyncEngine,
        table: str,
        rows: list[dict],
    ) -> dict:
        """
        Execute INSERT operation with run_sync pattern.

        Args:
            eng: AsyncEngine instance
            table: Table name
            rows: List of row dicts to insert

        Returns:
            Dict with inserted_count

        Raises:
            QueryError: If insert execution fails
        """
        try:
            async with eng.begin() as conn:
                # Use run_sync to handle table reflection properly
                def sync_insert(sync_conn):
                    meta = sa.MetaData()
                    tbl = sa.Table(table, meta, autoload_with=sync_conn)
                    # Filter out None values from rows to let DB handle defaults
                    clean_rows = [{k: v for k, v in row.items() if v is not None} for row in rows]
                    sync_conn.execute(sa.insert(tbl), clean_rows)
                    return len(clean_rows)

                count = await conn.run_sync(sync_insert)
                return {"inserted_count": count}

        except cls.query_errors as e:
            cls._handle_error(e, "query", query=f"INSERT INTO {table}")

    @classmethod
    async def _execute_update(
        cls,
        eng: AsyncEngine,
        table: str,
        update_data: list[dict],
        where_conditions: dict,
    ) -> dict:
        """
        Execute UPDATE operation with run_sync pattern.

        Args:
            eng: AsyncEngine instance
            table: Table name
            update_data: List of dicts with update values
            where_conditions: WHERE clause conditions

        Returns:
            Dict with updated_count

        Raises:
            QueryError: If update execution fails
        """
        try:
            async with eng.begin() as conn:
                # Use run_sync for table reflection
                def sync_update(sync_conn):
                    meta = sa.MetaData()
                    tbl = sa.Table(table, meta, autoload_with=sync_conn)

                    total_updated = 0
                    for data in update_data:
                        # Filter out None values and don't update primary keys
                        clean_data = {k: v for k, v in data.items() if v is not None and k != "id"}
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

        except cls.query_errors as e:
            cls._handle_error(e, "query")

    @classmethod
    async def _execute_upsert(
        cls,
        eng: AsyncEngine,
        table: str,
        rows: list[dict],
        conflict_columns: list[str],
    ) -> dict:
        """
        Execute UPSERT operation with run_sync pattern.

        Args:
            eng: AsyncEngine instance
            table: Table name
            rows: List of row dicts to upsert
            conflict_columns: Columns that define conflicts

        Returns:
            Dict with inserted_count, updated_count, total_count

        Raises:
            QueryError: If upsert execution fails
        """
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
                        clean_row = {k: v for k, v in row.items() if v is not None}

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
                            update_data = {k: v for k, v in clean_row.items() if k != "id"}
                            if update_data:
                                update_stmt = sa.update(tbl)
                                for col in conflict_columns:
                                    if col in clean_row:
                                        update_stmt = update_stmt.where(
                                            getattr(tbl.c, col) == clean_row[col]
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

        except cls.query_errors as e:
            cls._handle_error(e, "query")

    @classmethod
    def _validate_rows(
        cls,
        rows: list[dict],
        subj_cls: type[T],
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...] = (PydanticValidationError,),
    ) -> T | list[T]:
        """
        Convert database rows to model instances with validation.

        Args:
            rows: List of row dicts
            subj_cls: Target model class
            many: Whether to return list or single instance
            adapt_meth: Method name or callable for adaptation
            adapt_kw: Additional keyword arguments
            validation_errors: Tuple of validation error types to catch

        Returns:
            Model instance(s)

        Raises:
            ValidationError: If model validation fails
        """
        try:
            if many:
                return [dispatch_adapt_meth(adapt_meth, r, adapt_kw, subj_cls) for r in rows]
            return dispatch_adapt_meth(adapt_meth, rows[0], adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=rows[0] if not many else rows,
                errors=e.errors() if hasattr(e, "errors") else None,
            )

    @classmethod
    def _serialize_models(
        cls,
        items: list[T],
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
    ) -> list[dict]:
        """
        Convert model instances to database rows.

        Args:
            items: List of model instances
            adapt_meth: Method name or callable for serialization
            adapt_kw: Additional keyword arguments

        Returns:
            List of row dicts
        """
        return [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]

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
            raise ResourceError(f"Error accessing table '{name}': {e}", resource=name) from e

    # ---- incoming
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: SQLReadConfig | dict,  # TypedDict for IDE support
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (PydanticValidationError,),
        **kw,
    ) -> T | list[T]:
        try:
            # Get operation type (default: "select" for backward compatibility)
            operation = obj.get("operation", "select").lower()

            # Create engine using helper
            eng = await cls._create_engine(obj)

            # Handle different operations
            if operation == "select":
                # Execute SELECT using helper
                rows = await cls._execute_select(eng, obj)

                # Handle empty result set
                if not rows:
                    if many:
                        return []
                    cls._handle_error(
                        ValueError("No rows found matching the query"),
                        "resource",
                        resource=obj["table"],
                        selectors=obj.get("selectors", {}),
                    )

                # Validate rows using helper
                return cls._validate_rows(
                    rows, subj_cls, many, adapt_meth, adapt_kw, validation_errors
                )

            elif operation == "delete":
                # Execute DELETE using helper
                return await cls._execute_delete(eng, obj)

            elif operation == "raw_sql":
                # Execute RAW SQL using helper
                records = await cls._execute_raw_sql(eng, obj)

                # Handle empty results
                if not records or (isinstance(records, list) and len(records) == 0):
                    return [] if many else None

                # If records is a dict (affected_rows), return as-is
                if isinstance(records, dict):
                    return records

                # Try to convert to Pydantic models if possible
                try:
                    if subj_cls is not dict:  # Only convert if not using generic dict
                        if many:
                            return [
                                dispatch_adapt_meth(adapt_meth, r, adapt_kw, subj_cls)
                                for r in records
                            ]
                        return dispatch_adapt_meth(adapt_meth, records[0], adapt_kw, subj_cls)
                    else:
                        return records if many else records[0]
                except validation_errors as e:
                    # If validation fails, let _handle_error wrap it
                    cls._handle_error(
                        e,
                        "validation",
                        data=records[0] if not many else records,
                        errors=e.errors() if hasattr(e, "errors") else None,
                    )
                except TypeError:
                    # If conversion fails for other reasons, return raw dicts
                    return records if many else records[0]

            else:
                cls._handle_error(
                    ValueError(f"Unsupported operation '{operation}' for from_obj"),
                    "validation",
                    data=obj,
                )

        except PydapterError:
            raise
        except Exception as e:
            cls._handle_error(e, "query", unexpected=True)

    # ---- outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        try:
            # Validate required parameters
            if "table" not in kw:
                cls._handle_error(
                    ValueError("Missing required parameter 'table'"),
                    "validation",
                )

            table = kw["table"]

            # Get operation type (default: "insert" for backward compatibility)
            operation = kw.get("operation", "insert").lower()

            # Create engine using helper
            eng = await cls._create_engine(kw)

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"affected_count": 0}

            # Handle different operations
            if operation == "insert":
                # Serialize models using helper
                rows = cls._serialize_models(items, adapt_meth, adapt_kw)
                # Execute INSERT using helper
                return await cls._execute_insert(eng, table, rows)

            elif operation == "update":
                # Validate required parameters
                if "where" not in kw:
                    cls._handle_error(
                        ValueError("UPDATE operation requires 'where' parameter"),
                        "validation",
                    )

                where_conditions = kw["where"]
                # Serialize models using helper
                update_data = cls._serialize_models(items, adapt_meth, adapt_kw)
                # Execute UPDATE using helper
                return await cls._execute_update(eng, table, update_data, where_conditions)

            elif operation == "upsert":
                # Validate required parameters
                if "conflict_columns" not in kw:
                    cls._handle_error(
                        ValueError("UPSERT operation requires 'conflict_columns' parameter"),
                        "validation",
                    )

                conflict_columns = kw["conflict_columns"]
                # Serialize models using helper
                rows = cls._serialize_models(items, adapt_meth, adapt_kw)
                # Execute UPSERT using helper
                return await cls._execute_upsert(eng, table, rows, conflict_columns)

            else:
                cls._handle_error(
                    ValueError(f"Unsupported operation '{operation}' for to_obj"),
                    "validation",
                )

        except PydapterError:
            raise
        except Exception as e:
            cls._handle_error(e, "query", unexpected=True)
