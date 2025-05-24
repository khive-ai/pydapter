"""
AsyncPostgresAdapter - presets AsyncSQLAdapter for PostgreSQL/pgvector.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from ..exceptions import ConnectionError
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
    async def from_obj(cls, subj_cls, obj: dict, /, **kw):
        try:
            # Use the provided DSN if available, otherwise use the default
            engine_url = kw.get("dsn", cls.DEFAULT)
            if "dsn" in kw:
                # Convert the PostgreSQL URL to SQLAlchemy format
                if not engine_url.startswith("postgresql+asyncpg://"):
                    engine_url = engine_url.replace(
                        "postgresql://", "postgresql+asyncpg://"
                    )
            obj.setdefault("engine_url", engine_url)

            # Add PostgreSQL-specific error handling
            try:
                return await super().from_obj(subj_cls, obj, **kw)
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="async_pg",
                        url=engine_url,
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="async_pg",
                        url=engine_url,
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="async_pg",
                        url=engine_url,
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
    async def to_obj(cls, subj, /, **kw):
        try:
            # Use the provided DSN if available, otherwise use the default
            engine_url = kw.get("dsn", cls.DEFAULT)
            if "dsn" in kw:
                # Convert the PostgreSQL URL to SQLAlchemy format
                if not engine_url.startswith("postgresql+asyncpg://"):
                    engine_url = engine_url.replace(
                        "postgresql://", "postgresql+asyncpg://"
                    )
            kw.setdefault("engine_url", engine_url)

            # Add PostgreSQL-specific error handling
            try:
                return await super().to_obj(subj, **kw)
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="async_pg",
                        url=engine_url,
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="async_pg",
                        url=engine_url,
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="async_pg",
                        url=engine_url,
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
