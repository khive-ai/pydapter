"""
pydapter.async_core - async counterparts to the sync Adapter stack
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from .exceptions import (
    PYDAPTER_PYTHON_ERRORS,
    AdapterError,
    AdapterNotFoundError,
    ConfigurationError,
    ConnectionError,
    ParseError,
    QueryError,
    ResourceError,
)
from .exceptions import ValidationError as AdapterValidationError

T = TypeVar("T")


# --------------------------------------------------- dispatch_adapt_meth
def dispatch_adapt_meth(
    adapt_meth: str | Callable,
    obj: Any,
    adapt_kw: dict[str, Any] | None = None,
    cls: type | None = None,
) -> Any:
    """
    Dispatch adapt_meth as either a string method name or a callable.

    Args:
        adapt_meth: Method name (str) or callable function
        obj: Object to adapt (passed to method/callable)
        adapt_kw: Keyword arguments for the method/callable
        cls: Class to get method from (required if adapt_meth is str)

    Returns:
        Result of calling the method/callable
    """
    if callable(adapt_meth):
        return adapt_meth(obj, **(adapt_kw or {}))
    else:
        if cls is None:
            raise ValueError("cls required when adapt_meth is a string")
        return getattr(cls, adapt_meth)(obj, **(adapt_kw or {}))


# ------------------------------------------------------------ AsyncAdapterBase
class AsyncAdapterBase:
    """Base class providing _handle_error() for consistent exception wrapping in async adapters."""

    adapter_key: str = "base"

    # Exception category → PydapterError subclass mapping
    _error_mapping: dict[str, type] = {
        "parse": ParseError,
        "validation": AdapterValidationError,
        "connection": ConnectionError,
        "query": QueryError,
        "resource": ResourceError,
    }

    @classmethod
    def _sanitize_url(cls, url: str) -> str:
        """Sanitize URLs to remove credentials before logging."""
        if not isinstance(url, str):
            return url

        # Check for common URL patterns with credentials
        # postgresql://user:password@host:port/db → postgresql://user:***@host:port/db
        # mongodb://user:password@host:port/db → mongodb://user:***@host:port/db
        # http://user:password@host:port → http://user:***@host:port
        import re

        # Pattern: scheme://[user[:password]@]host
        pattern = r"((?:https?|postgresql|mongodb|mysql|redis)://[^:]+:)([^@]+)(@)"
        sanitized = re.sub(pattern, r"\1***\3", url)
        return sanitized

    @classmethod
    def _handle_error(cls, exc: Exception, category: str, **extra_details) -> None:
        """Wrap exception in appropriate PydapterError subclass with context."""
        error_class = cls._error_mapping.get(category, AdapterError)

        # Build error details - safely handle source/data truncation
        details = {
            "category": category,
            "original_exception": exc.__class__.__name__,
        }

        # Safely truncate source/data fields if present
        for key in ("source", "data"):
            if key in extra_details:
                value = extra_details[key]
                if isinstance(value, (str, bytes)):
                    # Truncate long strings/bytes to 100 chars
                    if len(value) > 100:
                        details[key] = f"{value[:100]}... (truncated)"
                    else:
                        details[key] = value
                elif isinstance(value, (list, tuple)):
                    # Truncate long lists/tuples (e.g., embeddings) to first 5 elements
                    if len(value) > 10:
                        details[key] = (
                            f"{type(value).__name__}([{', '.join(map(str, value[:5]))}, ...] len={len(value)})"
                        )
                    else:
                        details[key] = value
                elif isinstance(value, dict):
                    # Truncate large dicts to show only keys
                    if len(value) > 10:
                        keys = list(value.keys())[:5]
                        details[key] = f"dict(keys={keys}... len={len(value)})"
                    else:
                        details[key] = value
                else:
                    # For other types, include as-is
                    details[key] = value

        # Sanitize URL fields to remove credentials
        url_fields = ("url", "connection", "connection_string", "database_url", "dsn")
        for key, value in extra_details.items():
            if key not in ("source", "data"):
                if key in url_fields and isinstance(value, str):
                    # Sanitize URLs to remove passwords
                    details[key] = cls._sanitize_url(value)
                else:
                    details[key] = value

        # Add adapter_key if available
        if hasattr(cls, "adapter_key"):
            details["adapter"] = cls.adapter_key

        # Raise with original traceback preserved
        raise error_class(str(exc), **details) from exc


# ----------------------------------------------------------------- AsyncAdapter
@runtime_checkable
class AsyncAdapter(Protocol[T]):
    """Stateless, **async** conversion helper."""

    obj_key: ClassVar[str]

    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: Any,
        /,
        *,
        many: bool = False,
        adapt_meth: str = "model_validate",
        **kw,
    ) -> T | list[T]: ...

    @classmethod
    async def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str = "model_dump",
        **kw,
    ) -> Any: ...


# ------------------------------------------------------ AsyncAdapterRegistry
class AsyncAdapterRegistry:
    def __init__(self) -> None:
        self._reg: dict[str, type[AsyncAdapter]] = {}

    def register(self, adapter_cls: type[AsyncAdapter]) -> None:
        key = getattr(adapter_cls, "obj_key", None)
        if not key:
            raise ConfigurationError(
                "AsyncAdapter must define 'obj_key'", adapter_cls=adapter_cls.__name__
            )
        self._reg[key] = adapter_cls

    def get(self, obj_key: str) -> type[AsyncAdapter]:
        try:
            return self._reg[obj_key]
        except KeyError as exc:
            raise AdapterNotFoundError(
                f"No async adapter for '{obj_key}'", obj_key=obj_key
            ) from exc

    # convenience helpers
    async def adapt_from(
        self,
        subj_cls: type[T],
        obj,
        *,
        obj_key: str,
        adapt_meth: str = "model_validate",
        **kw,
    ):
        try:
            result = await self.get(obj_key).from_obj(subj_cls, obj, adapt_meth=adapt_meth, **kw)
            if result is None:
                raise AdapterError(f"Async adapter {obj_key} returned None", adapter=obj_key)
            return result
        except Exception as exc:
            if isinstance(exc, (AdapterError, *PYDAPTER_PYTHON_ERRORS)):
                raise

            # Wrap other exceptions with context
            raise AdapterError(
                f"Error in async adapt_from for {obj_key}", original_error=str(exc)
            ) from exc

    async def adapt_to(self, subj, *, obj_key: str, adapt_meth: str = "model_dump", **kw):
        try:
            result = await self.get(obj_key).to_obj(subj, adapt_meth=adapt_meth, **kw)
            if result is None:
                raise AdapterError(f"Async adapter {obj_key} returned None", adapter=obj_key)
            return result
        except Exception as exc:
            if isinstance(exc, (AdapterError, *PYDAPTER_PYTHON_ERRORS)):
                raise

            raise AdapterError(
                f"Error in async adapt_to for {obj_key}", original_error=str(exc)
            ) from exc


# -------------------------------------------------------------- AsyncAdaptable
class AsyncAdaptable:
    """
    Mixin that endows any Pydantic model with async adapt-from / adapt-to.
    """

    _async_registry: ClassVar[AsyncAdapterRegistry | None] = None

    # registry access
    @classmethod
    def _areg(cls) -> AsyncAdapterRegistry:
        if cls._async_registry is None:
            cls._async_registry = AsyncAdapterRegistry()
        return cls._async_registry

    @classmethod
    def register_async_adapter(cls, adapter_cls: type[AsyncAdapter]) -> None:
        cls._areg().register(adapter_cls)

    # helpers
    @classmethod
    async def adapt_from_async(cls, obj, *, obj_key: str, adapt_meth: str = "model_validate", **kw):
        return await cls._areg().adapt_from(cls, obj, obj_key=obj_key, adapt_meth=adapt_meth, **kw)

    async def adapt_to_async(self, *, obj_key: str, adapt_meth: str = "model_dump", **kw):
        return await self._areg().adapt_to(self, obj_key=obj_key, adapt_meth=adapt_meth, **kw)
