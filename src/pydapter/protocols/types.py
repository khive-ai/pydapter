"""
Basic types for protocols - maintained for backwards compatibility.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class Log(BaseModel):
    """Base Log model"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "some-uuid-string",
                "event_type": "example_event",
                "content": "This is an example log entry.",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"key": "value"},
                "created_at": "2023-10-01T12:00:00Z",
                "updated_at": "2023-10-01T12:00:00Z",
                "duration": 1.23,
                "status": "success",
                "error": None,
                "sha256": "abc123def456...",
            },
        },
    )

    id: str
    event_type: str
    content: str | None = None
    embedding: list[float] | None = None
    metadata: dict[str, Any] | None = None
    created_at: str | None = None  # ISO format string
    updated_at: str | None = None  # ISO format string
    duration: float | None = None
    status: str | None = None
    error: str | None = None
    sha256: str | None = None


__all__ = ("Log",)
