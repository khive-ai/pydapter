from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import field_serializer

__all__ = ("Identifiable",)


@runtime_checkable
class Identifiable(Protocol):
    id: UUID


class IdentifiableMixin(Identifiable):
    """Base class for objects with a unique identifier"""

    @field_serializer("id")
    def _serialize_ids(self, v: UUID) -> str:
        return str(v)

    def __hash__(self) -> int:
        """Returns the hash of the object."""
        return hash(self.id)
