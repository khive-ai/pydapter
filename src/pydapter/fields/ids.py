import contextlib
from typing import Union
from uuid import UUID, uuid4

from pydapter.exceptions import ValidationError
from pydapter.fields.types import Field

__all__ = (
    "ID_FROZEN",
    "ID_MUTABLE",
    "ID_NULLABLE",
    "validate_uuid",
    "serialize_uuid",
)


def validate_uuid(v: UUID | str, /, nullable: bool = False) -> UUID | None:
    if not v and nullable:
        return None
    if isinstance(v, UUID):
        return v
    with contextlib.suppress(ValueError):
        return UUID(str(v))
    raise ValidationError("id must be a valid UUID or UUID string")


def serialize_uuid(v: UUID, /) -> str:
    return str(v)


def uuid_validator(cls, v) -> UUID | None:
    return validate_uuid(v)


def nullable_uuid_validator(cls, v) -> UUID | None:
    return validate_uuid(v, nullable=True)


ID_FROZEN = Field(
    name="id",
    annotation=UUID,
    default_factory=uuid4,
    frozen=True,
    title="ID",
    validator=uuid_validator,
    description="Frozen Unique identifier",
    immutable=True,
)

ID_MUTABLE = Field(
    name="id",
    annotation=UUID,
    default_factory=uuid4,
    title="ID",
    validator=lambda cls, v: validate_uuid(v),
    immutable=True,
)

ID_NULLABLE = Field(
    name="nullable_id",
    annotation=Union[UUID, None],  # Use Union to avoid UnionType issues
    default=None,
    validator=lambda cls, v: validate_uuid(v, nullable=True),
    immutable=True,
)
