"""
AsyncPostgresAdapter - presets AsyncSQLAdapter for PostgreSQL/pgvector.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from ..exceptions import PydapterError
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

    adapter_key = "async_pg"
    obj_key = "async_pg"  # Backward compatibility
    DEFAULT = "postgresql+asyncpg://test:test@localhost/test"

    # -------- Helper Methods --------

    @classmethod
    def _detect_postgres_error_type(cls, error_str: str, url: str, exc: Exception) -> None:
        """
        Detect and raise appropriate PostgreSQL-specific errors.

        Args:
            error_str: Lowercase error message string
            url: Connection URL for context
            exc: Original exception

        Raises:
            ConnectionError: If PostgreSQL-specific error detected
        """
        error_str_lower = error_str.lower()

        if "authentication" in error_str_lower:
            cls._handle_error(
                exc,
                "connection",
                reason="authentication_failed",
                url=url,
            )
        elif "connection" in error_str_lower and "refused" in error_str_lower:
            cls._handle_error(
                exc,
                "connection",
                reason="connection_refused",
                url=url,
            )
        elif "does not exist" in error_str_lower and "database" in error_str_lower:
            cls._handle_error(
                exc,
                "connection",
                reason="database_not_found",
                url=url,
            )

    @classmethod
    def _prepare_config(cls, obj: dict | None = None, **kw) -> dict:
        """
        Prepare configuration with default PostgreSQL connection string and driver conversion.

        Args:
            obj: Config dict (for from_obj)
            kw: Keyword args (for to_obj)

        Returns:
            Config dict with defaults applied
        """
        if obj is not None:
            config = obj.copy()
        else:
            config = kw.copy()

        # Validate only one engine parameter
        engine_params = sum(["engine" in config, "dsn" in config, "engine_url" in config])

        if engine_params > 1:
            cls._handle_error(
                ValueError("Multiple engine parameters provided"),
                "validation",
                data=config,
            )

        # Handle DSN/engine setup
        if "engine" not in config:
            # Get DSN from config or use default
            if "dsn" in config:
                dsn = config["dsn"]
            elif "engine_url" in config:  # Backward compatibility
                dsn = config["engine_url"]
                config["dsn"] = dsn  # Convert to dsn
                del config["engine_url"]  # Remove to avoid confusion
            else:
                dsn = cls.DEFAULT
                config["dsn"] = dsn

            # Convert PostgreSQL URL to SQLAlchemy format if needed
            # BUT skip this for SQLite DSNs
            if dsn.startswith("sqlite"):
                # Keep SQLite DSN as-is
                pass
            elif not dsn.startswith("postgresql+asyncpg://"):
                config["dsn"] = dsn.replace("postgresql://", "postgresql+asyncpg://")

        return config

    @classmethod
    async def from_obj(
        cls,
        subj_cls,
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        try:
            # Prepare config with defaults using helper
            # Handle DSN from kw if present
            if "dsn" in kw:
                obj["dsn"] = kw["dsn"]
            obj = cls._prepare_config(obj)

            # Call parent AsyncSQLAdapter
            try:
                return await super().from_obj(
                    subj_cls,
                    obj,
                    many=many,
                    adapt_meth=adapt_meth,
                    adapt_kw=adapt_kw,
                    **kw,
                )
            except Exception as e:
                # Detect PostgreSQL-specific errors using helper
                cls._detect_postgres_error_type(str(e), obj.get("dsn", cls.DEFAULT), e)
                # If not PostgreSQL-specific, re-raise
                raise

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Outer safety net
            cls._handle_error(
                e,
                "connection",
                url=obj.get("dsn", cls.DEFAULT),
                unexpected=True,
            )

    @classmethod
    async def to_obj(
        cls,
        subj,
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        try:
            # Prepare config with defaults using helper
            kw = cls._prepare_config(None, **kw)

            # Call parent AsyncSQLAdapter
            try:
                return await super().to_obj(
                    subj,
                    many=many,
                    adapt_meth=adapt_meth,
                    adapt_kw=adapt_kw,
                    **kw,
                )
            except Exception as e:
                # Detect PostgreSQL-specific errors using helper
                cls._detect_postgres_error_type(str(e), kw.get("dsn", cls.DEFAULT), e)
                # If not PostgreSQL-specific, re-raise
                raise

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Outer safety net
            cls._handle_error(
                e,
                "connection",
                url=kw.get("dsn", cls.DEFAULT),
                unexpected=True,
            )
