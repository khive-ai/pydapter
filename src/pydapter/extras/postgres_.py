"""
PostgresAdapter - thin preset over SQLAdapter (pgvector-ready if you add vec column).
"""

from __future__ import annotations

from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T
from .sql_ import SQLAdapter

_CUSTOM_ERROR = (ConnectionError, QueryError, ResourceError, ValidationError)


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

    obj_key = "postgres"
    DEFAULT = "postgresql+psycopg://user:pass@localhost/db"

    @classmethod
    def from_obj(
        cls,
        subj_cls,
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Set default connection string if not provided
        obj.setdefault("engine_url", cls.DEFAULT)

        # Add PostgreSQL-specific error handling
        try:
            return super().from_obj(
                subj_cls,
                obj,
                many=many,
                adapt_meth=adapt_meth,
                adapt_kw=adapt_kw,
                **kw,
            )
        except Exception as e:
            # Check for common PostgreSQL-specific errors
            error_str = str(e).lower()
            if "authentication" in error_str:
                raise ConnectionError.from_adapter(
                    cls,
                    "PostgreSQL authentication failed",
                    url=obj["engine_url"],
                    cause=e,
                )
            elif "connection" in error_str and "refused" in error_str:
                raise ConnectionError.from_adapter(
                    cls, "PostgreSQL connection refused", url=obj["engine_url"], cause=e
                )
            elif "does not exist" in error_str and "database" in error_str:
                raise ConnectionError.from_adapter(
                    cls,
                    "PostgreSQL database does not exist",
                    url=obj["engine_url"],
                    cause=e,
                )
            # Re-raise the original exception
            raise

    @classmethod
    def to_obj(
        cls,
        subj,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Set default connection string if not provided
        kw.setdefault("engine_url", cls.DEFAULT)

        # Add PostgreSQL-specific error handling
        try:
            return super().to_obj(
                subj, many=many, adapt_meth=adapt_meth, adapt_kw=adapt_kw, **kw
            )
        except Exception as e:
            # Check for common PostgreSQL-specific errors
            error_str = str(e).lower()
            if "authentication" in error_str:
                raise ConnectionError.from_adapter(
                    cls,
                    "PostgreSQL authentication failed",
                    url=kw["engine_url"],
                    cause=e,
                )
            elif "connection" in error_str and "refused" in error_str:
                raise ConnectionError.from_adapter(
                    cls, "PostgreSQL connection refused", url=kw["engine_url"], cause=e
                )
            elif "does not exist" in error_str and "database" in error_str:
                raise ConnectionError.from_adapter(
                    cls,
                    "PostgreSQL database does not exist",
                    url=kw["engine_url"],
                    cause=e,
                )
            # Re-raise the original exception
            raise
