"""
Basic types for protocols - maintained for backwards compatibility.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pydapter.fields.types import Embedding


class Log(BaseModel):
    """Basic log model for backwards compatibility."""

    id: str
    event_type: str
    content: str | None = None
    embedding: Embedding | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


__all__ = ("Log",)
