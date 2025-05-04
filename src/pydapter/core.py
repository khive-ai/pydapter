"""
pydapter.core - Adapter protocol, registry, Adaptable mix-in.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


# ------------------------------------------------------------------ Adapter
@runtime_checkable
class Adapter(Protocol[T]):
    """Stateless conversion helper."""

    obj_key: ClassVar[str]

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many: bool = False, **kw): ...

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw): ...


# ----------------------------------------------------------- AdapterRegistry
class AdapterRegistry:
    def __init__(self) -> None:
        self._reg: dict[str, type[Adapter]] = {}

    def register(self, adapter_cls: type[Adapter]) -> None:
        key = getattr(adapter_cls, "obj_key", None)
        if not key:
            from .exceptions import ConfigurationError

            raise ConfigurationError(
                "Adapter must define 'obj_key'", adapter_cls=adapter_cls.__name__
            )
        self._reg[key] = adapter_cls

    def get(self, obj_key: str) -> type[Adapter]:
        try:
            return self._reg[obj_key]
        except KeyError as exc:
            from .exceptions import AdapterNotFoundError

            raise AdapterNotFoundError(
                f"No adapter registered for '{obj_key}'", obj_key=obj_key
            ) from exc

    # convenience
    def adapt_from(self, subj_cls: type[T], obj, *, obj_key: str, **kw):
        try:
            result = self.get(obj_key).from_obj(subj_cls, obj, **kw)
            if result is None:
                from .exceptions import AdapterError

                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result
        except Exception as exc:
            # Import here to avoid circular imports
            from .exceptions import (
                AdapterError,
                AdapterNotFoundError,
                ConfigurationError,
                ConnectionError,
                ParseError,
                QueryError,
                ResourceError,
                ValidationError,
            )

            # Re-raise our custom exceptions
            if isinstance(
                exc,
                (
                    AdapterNotFoundError,
                    ConfigurationError,
                    ConnectionError,
                    ParseError,
                    QueryError,
                    ResourceError,
                    ValidationError,
                ),
            ):
                raise

            # Re-raise adapter-related errors and ValueError for tests
            if isinstance(exc, (KeyError, ImportError, AttributeError, ValueError)):
                raise

            # Wrap other exceptions with context
            raise AdapterError(
                f"Error adapting from {obj_key}", original_error=str(exc)
            ) from exc

    def adapt_to(self, subj, *, obj_key: str, **kw):
        try:
            result = self.get(obj_key).to_obj(subj, **kw)
            if result is None:
                from .exceptions import AdapterError

                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result
        except Exception as exc:
            # Import here to avoid circular imports
            from .exceptions import (
                AdapterError,
                AdapterNotFoundError,
                ConfigurationError,
                ConnectionError,
                ParseError,
                QueryError,
                ResourceError,
                ValidationError,
            )

            # Re-raise our custom exceptions
            if isinstance(
                exc,
                (
                    AdapterNotFoundError,
                    ConfigurationError,
                    ConnectionError,
                    ParseError,
                    QueryError,
                    ResourceError,
                    ValidationError,
                ),
            ):
                raise

            # Re-raise adapter-related errors and ValueError for tests
            if isinstance(exc, (KeyError, ImportError, AttributeError, ValueError)):
                raise

            # Wrap other exceptions with context
            raise AdapterError(
                f"Error adapting to {obj_key}", original_error=str(exc)
            ) from exc


# ----------------------------------------------------------------- Adaptable
class Adaptable:
    """Mixin that endows any Pydantic model with adapt-from / adapt-to."""

    _adapter_registry: ClassVar[AdapterRegistry | None] = None

    # registry
    @classmethod
    def _registry(cls) -> AdapterRegistry:
        if cls._adapter_registry is None:
            cls._adapter_registry = AdapterRegistry()
        return cls._adapter_registry

    @classmethod
    def register_adapter(cls, adapter_cls: type[Adapter]) -> None:
        cls._registry().register(adapter_cls)

    # high-level helpers
    @classmethod
    def adapt_from(cls, obj, *, obj_key: str, **kw):
        return cls._registry().adapt_from(cls, obj, obj_key=obj_key, **kw)

    def adapt_to(self, *, obj_key: str, **kw):
        return self._registry().adapt_to(self, obj_key=obj_key, **kw)
