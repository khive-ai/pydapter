from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from .utils import validate_uuid

__all__ = ("Identifiable",)


class Identifiable(BaseModel):
    """Base class for objects with a unique identifier and creation timestamp."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the element.",
        frozen=True,
    )

    @field_serializer("id")
    def _serialize_ids(self, v: UUID) -> str:
        return str(v)

    @field_validator("id", mode="before")
    def _validate_ids(cls, v: str | UUID) -> UUID:
        return validate_uuid(v)

    def __hash__(self) -> int:
        """Returns the hash of the object."""
        return hash(self.id)
