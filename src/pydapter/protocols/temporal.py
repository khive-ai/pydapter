from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import field_serializer

__all__ = (
    "Temporal",
    "TemporalMixin",
)


@runtime_checkable
class Temporal(Protocol):
    created_at: datetime
    updated_at: datetime


class TemporalMixin:
    if TYPE_CHECKING:
        created_at: datetime
        updated_at: datetime

    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(timezone.utc)

    @field_serializer("updated_at", "created_at")
    def _serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()
