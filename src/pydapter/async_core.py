"""
pydapter.async_core - async counterparts to the sync Adapter stack
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from .exceptions import (
    PYDAPTER_PYTHON_ERRORS,
    AdapterError,
    AdapterNotFoundError,
    ConfigurationError,
)

T = TypeVar("T")


# ----------------------------------------------------------------- AsyncAdapter
@runtime_checkable
class AsyncAdapter(Protocol[T]):
    """Stateless, **async** conversion helper."""

    obj_key: ClassVar[str]

    @classmethod
    async def from_obj(
        cls, subj_cls: type[T], obj: Any, /, *, many: bool = False, **kw
    ) -> T | list[T]: ...

    @classmethod
    async def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw) -> Any: ...


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
    async def adapt_from(self, subj_cls: type[T], obj, *, obj_key: str, **kw):
        try:
            result = await self.get(obj_key).from_obj(subj_cls, obj, **kw)
            if result is None:
                raise AdapterError(
                    f"Async adapter {obj_key} returned None", adapter=obj_key
                )
            return result
        except Exception as exc:
            if isinstance(exc, AdapterError) or isinstance(exc, PYDAPTER_PYTHON_ERRORS):
                raise

            # Wrap other exceptions with context
            raise AdapterError(
                f"Error in async adapt_from for {obj_key}", original_error=str(exc)
            ) from exc

    async def adapt_to(self, subj, *, obj_key: str, **kw):
        try:
            result = await self.get(obj_key).to_obj(subj, **kw)
            if result is None:
                raise AdapterError(
                    f"Async adapter {obj_key} returned None", adapter=obj_key
                )
            return result
        except Exception as exc:
            if isinstance(exc, AdapterError) or isinstance(exc, PYDAPTER_PYTHON_ERRORS):
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
    async def adapt_from_async(cls, obj, *, obj_key: str, **kw):
        return await cls._areg().adapt_from(cls, obj, obj_key=obj_key, **kw)

    async def adapt_to_async(self, *, obj_key: str, **kw):
        return await self._areg().adapt_to(self, obj_key=obj_key, **kw)
