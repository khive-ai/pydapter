"""
PostgresAdapter - thin preset over SQLAdapter (pgvector-ready if you add vec column).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from ..exceptions import PydapterError
from .sql_ import SQLAdapter

T = TypeVar("T", bound=BaseModel)


class PostgresAdapter(SQLAdapter[T]):
    """
    PostgreSQL-specific adapter extending SQLAdapter with PostgreSQL optimizations.

    This adapter provides:
    - PostgreSQL-specific connection handling and error messages
    - Default PostgreSQL connection string
    - Enhanced error handling for common PostgreSQL issues
    - Support for pgvector when vector columns are present

    Attributes:
        obj_key: The key identifier for this adapter type ("postgres")
        DEFAULT: Default PostgreSQL connection string

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.extras.postgres_ import PostgresAdapter

        class User(BaseModel):
            id: int
            name: str
            email: str

        # Query with custom connection
        query_config = {
            "query": "SELECT id, name, email FROM users WHERE active = true",
            "engine_url": "postgresql+psycopg://user:pass@localhost/mydb"
        }
        users = PostgresAdapter.from_obj(User, query_config, many=True)

        # Insert with default connection
        insert_config = {
            "table": "users",
            "engine_url": "postgresql+psycopg://user:pass@localhost/mydb"
        }
        new_users = [User(id=1, name="John", email="john@example.com")]
        PostgresAdapter.to_obj(new_users, insert_config, many=True)
        ```
    """

    adapter_key = "postgres"
    obj_key = "postgres"  # Backward compatibility
    DEFAULT = "postgresql+psycopg://user:pass@localhost/db"

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
        Prepare configuration with default PostgreSQL connection string.

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

        config.setdefault("engine_url", cls.DEFAULT)
        return config

    @classmethod
    def from_obj(
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
            # Prepare config with defaults
            obj = cls._prepare_config(obj)

            # Call parent SQLAdapter
            try:
                return super().from_obj(
                    subj_cls, obj, many=many, adapt_meth=adapt_meth, adapt_kw=adapt_kw, **kw
                )
            except Exception as e:
                # Detect PostgreSQL-specific errors
                cls._detect_postgres_error_type(str(e), obj["engine_url"], e)
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
                url=obj.get("engine_url", cls.DEFAULT),
                unexpected=True,
            )

    @classmethod
    def to_obj(
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
            # Prepare config with defaults
            kw = cls._prepare_config(None, **kw)

            # Call parent SQLAdapter
            try:
                return super().to_obj(
                    subj, many=many, adapt_meth=adapt_meth, adapt_kw=adapt_kw, **kw
                )
            except Exception as e:
                # Detect PostgreSQL-specific errors
                cls._detect_postgres_error_type(str(e), kw["engine_url"], e)
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
                url=kw.get("engine_url", cls.DEFAULT),
                unexpected=True,
            )
