"""
PostgresAdapter - thin preset over SQLAdapter (pgvector-ready if you add vec column).
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from ..exceptions import ConnectionError
from .sql_ import SQLAdapter

T = TypeVar("T", bound=BaseModel)


class PostgresAdapter(SQLAdapter[T]):  # type: ignore[type-arg]
    obj_key = "postgres"
    DEFAULT = "postgresql+psycopg://user:pass@localhost/db"

    @classmethod
    def from_obj(cls, subj_cls, obj: dict, /, **kw):
        try:
            # Set default connection string if not provided
            obj.setdefault("engine_url", cls.DEFAULT)

            # Add PostgreSQL-specific error handling
            try:
                return super().from_obj(subj_cls, obj, **kw)
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="postgres",
                        url=obj["engine_url"],
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="postgres",
                        url=obj["engine_url"],
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="postgres",
                        url=obj["engine_url"],
                    ) from e
                # Re-raise the original exception
                raise

        except ConnectionError:
            # Re-raise ConnectionError
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ConnectionError(
                f"Unexpected error in PostgreSQL adapter: {e}",
                adapter="postgres",
                url=obj.get("engine_url", cls.DEFAULT),
            ) from e

    @classmethod
    def to_obj(cls, subj, /, **kw):
        try:
            # Set default connection string if not provided
            kw.setdefault("engine_url", cls.DEFAULT)

            # Add PostgreSQL-specific error handling
            try:
                return super().to_obj(subj, **kw)
            except Exception as e:
                # Check for common PostgreSQL-specific errors
                error_str = str(e).lower()
                if "authentication" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL authentication failed: {e}",
                        adapter="postgres",
                        url=kw["engine_url"],
                    ) from e
                elif "connection" in error_str and "refused" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL connection refused: {e}",
                        adapter="postgres",
                        url=kw["engine_url"],
                    ) from e
                elif "does not exist" in error_str and "database" in error_str:
                    raise ConnectionError(
                        f"PostgreSQL database does not exist: {e}",
                        adapter="postgres",
                        url=kw["engine_url"],
                    ) from e
                # Re-raise the original exception
                raise

        except ConnectionError:
            # Re-raise ConnectionError
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ConnectionError(
                f"Unexpected error in PostgreSQL adapter: {e}",
                adapter="postgres",
                url=kw.get("engine_url", cls.DEFAULT),
            ) from e
