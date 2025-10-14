"""
pydapter.core - Adapter protocol, registry, Adaptable mix-in.
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

T = TypeVar("T", contravariant=True)


# ---------------------------------------------------------------- Dispatcher
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


# ------------------------------------------------------------------ Adapter
@runtime_checkable
class Adapter(Protocol[T]):
    """
    Protocol for stateless data format adapters.

    Attributes:
        adapter_key: Unique identifier (e.g., "csv", "json")
        obj_key: Backward compatibility alias
        parse_errors: Exceptions during parsing
        connection_errors: Exceptions during connection (DB adapters)
        query_errors: Exceptions during query execution (DB adapters)
    """

    adapter_key: ClassVar[str]
    obj_key: ClassVar[str]  # Backward compatibility

    # Declarative exception handling (optional - adapters can define these)
    parse_errors: ClassVar[tuple[type[Exception], ...]]
    connection_errors: ClassVar[tuple[type[Exception], ...]]
    query_errors: ClassVar[tuple[type[Exception], ...]]

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: Any,
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict[str, Any] | None = None,
        validation_errors: tuple[type[Exception], ...] | None = None,
        **kw: Any,
    ) -> T | list[T]:
        """Convert from external format to Python object(s)."""
        ...

    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict[str, Any] | None = None,
        **kw: Any,
    ) -> Any:
        """Convert from Python object(s) to external format."""
        ...


# ------------------------------------------------------------ AdapterBase
class AdapterBase:
    """Base class providing _handle_error() for consistent exception wrapping."""

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
                    extra_details[key] = value[:100] if len(value) > 100 else value

        details.update(extra_details)

        # Get adapter key safely
        adapter_key = getattr(cls, "adapter_key", None) or getattr(cls, "obj_key", "unknown")

        # Raise wrapped exception with cause chain
        raise error_class(
            message=str(exc),
            adapter=adapter_key,
            details=details,
            cause=exc,
        ) from exc


# ----------------------------------------------------------- AdapterRegistry
class AdapterRegistry:
    """Registry for managing data format adapters."""

    def __init__(self) -> None:
        self._reg: dict[str, type[Adapter]] = {}

    def register(self, adapter_cls: type[Adapter]) -> None:
        """Register adapter class (must define adapter_key or obj_key)."""
        # Try adapter_key first (new), fall back to obj_key (backward compat)
        key = getattr(adapter_cls, "adapter_key", None) or getattr(adapter_cls, "obj_key", None)
        if not key:
            raise ConfigurationError(
                "Adapter must define 'adapter_key' or 'obj_key'", adapter_class=adapter_cls.__name__
            )
        self._reg[key] = adapter_cls

    def get(self, obj_key: str) -> type[Adapter]:
        """Retrieve adapter class by key."""
        try:
            return self._reg[obj_key]
        except KeyError as exc:
            raise AdapterNotFoundError(
                f"No adapter registered for '{obj_key}'", obj_key=obj_key
            ) from exc

    def adapt_from(
        self,
        subj_cls: type[T],
        obj: Any,
        *,
        obj_key: str,
        adapt_meth: str = "model_validate",
        **kw: Any,
    ) -> T | list[T]:
        """Convert from external format to Python object(s)."""
        try:
            result = self.get(obj_key).from_obj(subj_cls, obj, adapt_meth=adapt_meth, **kw)
            if result is None:
                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result

        except Exception as exc:
            if isinstance(exc, (AdapterError, *PYDAPTER_PYTHON_ERRORS)):
                raise

            raise AdapterError(f"Error adapting from {obj_key}", original_error=str(exc)) from exc

    def adapt_to(
        self, subj: Any, *, obj_key: str, adapt_meth: str = "model_dump", **kw: Any
    ) -> Any:
        """Convert from Python object(s) to external format."""
        try:
            result = self.get(obj_key).to_obj(subj, adapt_meth=adapt_meth, **kw)
            if result is None:
                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result

        except Exception as exc:
            if isinstance(exc, (AdapterError, *PYDAPTER_PYTHON_ERRORS)):
                raise

            raise AdapterError(f"Error adapting to {obj_key}", original_error=str(exc)) from exc


# ----------------------------------------------------------------- Adaptable
class Adaptable:
    """Mixin adding adapter functionality to Python classes."""

    @classmethod
    def _registry(cls) -> AdapterRegistry:
        """Get or create per-class adapter registry."""
        # Use a unique attribute name per class to avoid ClassVar sharing
        registry_attr = f"__pydapter_registry_{cls.__name__}_{id(cls)}"
        if not hasattr(cls, registry_attr):
            setattr(cls, registry_attr, AdapterRegistry())
        return getattr(cls, registry_attr)

    @classmethod
    def register_adapter(cls, adapter_cls: type[Adapter]) -> None:
        """Register adapter with this model."""
        cls._registry().register(adapter_cls)

    @classmethod
    def adapt_from(
        cls, obj: Any, *, obj_key: str, adapt_meth: str = "model_validate", **kw: Any
    ) -> Any:
        """Create instance(s) from external format."""
        return cls._registry().adapt_from(cls, obj, obj_key=obj_key, adapt_meth=adapt_meth, **kw)

    def adapt_to(self, *, obj_key: str, adapt_meth: str = "model_dump", **kw: Any) -> Any:
        """Convert instance to external format."""
        return self._registry().adapt_to(self, obj_key=obj_key, adapt_meth=adapt_meth, **kw)
