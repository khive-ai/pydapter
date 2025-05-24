from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

from pydantic import field_serializer

if TYPE_CHECKING:
    pass

__all__ = ("Identifiable",)


@runtime_checkable
class Identifiable(Protocol):
    id: UUID


class IdentifiableMixin:
    """Base class for objects with a unique identifier"""

    if TYPE_CHECKING:
        id: UUID

    @field_serializer("id")
    def _serialize_ids(self, v: UUID) -> str:
        return str(v)

    def __hash__(self) -> int:
        """Returns the hash of the object."""
        return hash(self.id)
