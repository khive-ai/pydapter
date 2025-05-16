# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_serializer, field_validator

from .utils import convert_to_datetime


class Temporal(BaseModel):
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
