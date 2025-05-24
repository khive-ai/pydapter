import contextlib
from datetime import datetime, timezone

from pydapter.exceptions import ValidationError
from pydapter.fields.types import Field

__all__ = (
    "DATETIME",
    "DATETIME_NULLABLE",
    "validate_datetime",
    "datetime_serializer",
)


def validate_datetime(
    v: datetime | str,
    /,
    nullable: bool = False,
) -> datetime | None:
    if not v and nullable:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(v)
    raise ValidationError(
        "Invalid datetime format, must be ISO 8601 or datetime object"
    )


def datetime_serializer(v: datetime, /) -> str:
    return v.isoformat()


def datetime_validator(cls, v):
    return validate_datetime(v)


def nullable_datetime_validator(cls, v):
    return validate_datetime(v, nullable=True)


DATETIME = Field(
    name="datetime_field",
    annotation=datetime,
    default_factory=lambda: datetime.now(tz=timezone.utc),
    validator=datetime_validator,
    immutable=True,
)

DATETIME_NULLABLE = Field(
    name="nullable_datetime_field",
    annotation=type(None),  # Simplified to avoid UnionType issues
    default=None,
    validator=nullable_datetime_validator,
    immutable=True,
)
