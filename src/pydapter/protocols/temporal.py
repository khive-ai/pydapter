from datetime import datetime, timezone

from pydantic import Field, field_serializer, field_validator

from .identifiable import Identifiable
from .utils import convert_to_datetime


class Temporal(Identifiable):
    """Allows for updating the last updated timestamp."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp for the element.",
        frozen=True,
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last updated timestamp for the element.",
    )

    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(timezone.utc)

    @field_serializer("updated_at", "created_at")
    def _serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()

    @field_validator("updated_at", "created_at", mode="before")
    def _validate_datetime(cls, v: str | datetime) -> datetime:
        return convert_to_datetime(v)
