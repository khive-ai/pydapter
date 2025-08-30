"""
AsyncPostgresAdapter - presets AsyncSQLAdapter for PostgreSQL/pgvector.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from ..exceptions import ConnectionError
from ..exceptions import ValidationError as AdapterValidationError
from .async_sql_ import AsyncSQLAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncPostgresAdapter(AsyncSQLAdapter[T]):
    """
    Asynchronous PostgreSQL adapter extending AsyncSQLAdapter with PostgreSQL-specific optimizations.

    This adapter provides:
    - Async PostgreSQL operations using asyncpg driver
    - Enhanced error handling for PostgreSQL-specific issues
    - Support for pgvector when vector columns are present
    - Default PostgreSQL connection string management

    Attributes:
        obj_key: The key identifier for this adapter type ("async_pg")
        DEFAULT: Default PostgreSQL+asyncpg connection string

    Example:
        ```python
        import asyncio
        from pydantic import BaseModel
        from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

        class User(BaseModel):
            id: int
            name: str
            email: str

        async def main():
            # Query with custom connection
            query_config = {
                "query": "SELECT id, name, email FROM users WHERE active = true",
                "dsn": "postgresql+asyncpg://user:pass@localhost/mydb"
            }
            users = await AsyncPostgresAdapter.from_obj(User, query_config, many=True)

            # Insert with default connection
            insert_config = {
                "table": "users"
            }
            new_users = [User(id=1, name="John", email="john@example.com")]
            await AsyncPostgresAdapter.to_obj(new_users, insert_config, many=True)

        asyncio.run(main())
        ```
    """

    obj_key = "async_pg"
    DEFAULT = "postgresql+asyncpg://test:test@localhost/test"

    @classmethod
    async def from_obj(
        cls,
        subj_cls,
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
        **kw,
    ):
        try:
            # Validate only one engine parameter is provided
            engine_params = sum(
                ["engine" in obj, "dsn" in obj, "dsn" in kw, "engine_url" in obj]
            )

            if engine_params > 1:
                raise AdapterValidationError(
                    "Multiple engine parameters provided. Use only one of: 'engine', 'dsn', or 'engine_url'"
                )

            # Handle DSN/engine setup
            if "engine" not in obj:
                # Get DSN from obj, kw, or use default
                if "dsn" in obj:
                    dsn = obj["dsn"]
                elif "dsn" in kw:
                    dsn = kw["dsn"]
                    obj["dsn"] = dsn  # Move to obj for parent class
                elif "engine_url" in obj:  # Backward compatibility
                    dsn = obj["engine_url"]
                    obj["dsn"] = dsn  # Convert to dsn
                    del obj["engine_url"]  # Remove to avoid confusion
                else:
                    dsn = cls.DEFAULT
                    obj["dsn"] = dsn

                # Convert PostgreSQL URL to SQLAlchemy format if needed
                # BUT skip this for SQLite DSNs
                if dsn.startswith("sqlite"):
                    # Keep SQLite DSN as-is
                    pass
                elif not dsn.startswith("postgresql+asyncpg://"):
                    obj["dsn"] = dsn.replace("postgresql://", "postgresql+asyncpg://")

            # Add PostgreSQL-specific error handling
            try:
                return await super().from_obj(
                    subj_cls, obj, many=many, adapt_meth=adapt_meth, **kw
                )
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                conn_url = obj.get("dsn", obj.get("engine_url", cls.DEFAULT))
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                # Re-raise the original exception
                raise

        except ConnectionError:
            # Re-raise ConnectionError
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ConnectionError(
                f"Unexpected error in async PostgreSQL adapter: {e}",
                adapter="async_pg",
                url=obj.get("engine_url", cls.DEFAULT),
            ) from e

    @classmethod
    async def to_obj(
        cls, subj, /, *, many: bool = True, adapt_meth: str = "model_dump", **kw
    ):
        try:
            # Validate only one engine parameter is provided
            engine_params = sum(["engine" in kw, "dsn" in kw, "engine_url" in kw])

            if engine_params > 1:
                raise AdapterValidationError(
                    "Multiple engine parameters provided. Use only one of: 'engine', 'dsn', or 'engine_url'"
                )

            # Handle DSN/engine setup
            if "engine" not in kw:
                # Get DSN from kw or use default
                if "dsn" in kw:
                    dsn = kw["dsn"]
                elif "engine_url" in kw:  # Backward compatibility
                    dsn = kw["engine_url"]
                    kw["dsn"] = dsn  # Convert to dsn
                    del kw["engine_url"]  # Remove to avoid confusion
                else:
                    dsn = cls.DEFAULT
                    kw["dsn"] = dsn

                # Convert PostgreSQL URL to SQLAlchemy format if needed
                if not dsn.startswith("postgresql+asyncpg://"):
                    kw["dsn"] = dsn.replace("postgresql://", "postgresql+asyncpg://")

            # Add PostgreSQL-specific error handling
            try:
                return await super().to_obj(
                    subj, many=many, adapt_meth=adapt_meth, **kw
                )
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                conn_url = kw.get("dsn", kw.get("engine_url", cls.DEFAULT))
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="async_pg",
                        url=conn_url,
                    ) from e
                # Re-raise the original exception
                raise

        except ConnectionError:
            # Re-raise ConnectionError
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ConnectionError(
                f"Unexpected error in async PostgreSQL adapter: {e}",
                adapter="async_pg",
                url=kw.get("engine_url", cls.DEFAULT),
            ) from e
