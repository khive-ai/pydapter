"""
pydapter.core – Adapter protocol, registry, Adaptable mix-in.
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
            raise AttributeError("Adapter must define 'obj_key'")
        self._reg[key] = adapter_cls

    def get(self, obj_key: str) -> type[Adapter]:
        try:
            return self._reg[obj_key]
        except KeyError as exc:
            raise KeyError(f"No adapter registered for '{obj_key}'") from exc

    # convenience
    def adapt_from(self, subj_cls: type[T], obj, *, obj_key: str, **kw):
        return self.get(obj_key).from_obj(subj_cls, obj, **kw)

    def adapt_to(self, subj, *, obj_key: str, **kw):
        return self.get(obj_key).to_obj(subj, **kw)


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
