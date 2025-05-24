"""
Basic types for protocols - maintained for backwards compatibility.
"""

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
    created_at: str | None = None  # ISO format string
    updated_at: str | None = None  # ISO format string
    duration: float | None = None
    status: str | None = None
    error: str | None = None
    sha256: str | None = None

    class Config:
        arbitrary_types_allowed = True


__all__ = ("Log",)
