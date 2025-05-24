from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import field_serializer

from pydapter.fields.dts import UTC

__all__ = (
    "Temporal",
    "TemporalMixin",
)


@runtime_checkable
class Temporal(Protocol):
    created_at: datetime
    updated_at: datetime


class TemporalMixin:
    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(UTC)

    @field_serializer("updated_at", "created_at")
    def _serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()
