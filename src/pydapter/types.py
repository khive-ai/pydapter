"""Core types and lionagi-compatible error interface."""

from __future__ import annotations

from typing import Any, ClassVar

__all__ = ("BaseError",)


class BaseError(Exception):
    """Lionagi-compatible base error class."""

    default_message: ClassVar[str] = "Error"
    default_status_code: ClassVar[int] = 500
    __slots__ = ("message", "details", "status_code")

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message or self.default_message)
        if cause:
            self.__cause__ = cause  # preserves traceback
        self.message = message or self.default_message
        self.details = details or {}
        self.status_code = status_code or type(self).default_status_code

    def __str__(self) -> str:
        details_str = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
        if details_str:
            return f"{self.message} ({details_str})"
        return self.message

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to details fields."""
        if name == "context":
            # Backward compatibility: context is alias for details
            return self.details
        if name in self.details:
            return self.details[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def to_dict(self, *, include_cause: bool = False) -> dict[str, Any]:
        """Serialize to dict for logging/API responses."""
        data = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            **({"details": self.details} if self.details else {}),
        }
        if include_cause and (cause := self.get_cause()):
            data["cause"] = repr(cause)
        return data

    def get_cause(self) -> Exception | None:
        """Get __cause__ if any."""
        return self.__cause__ if hasattr(self, "__cause__") else None

    @classmethod
    def from_value(
        cls,
        value: Any,
        *,
        expected: str | None = None,
        message: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        **extra: Any,
    ):
        """Create error from value with type/expected info in details."""
        details = {
            "value": value,
            "type": type(value).__name__,
            **({"expected": expected} if expected else {}),
            **extra,
        }
        return cls(message=message, details=details, status_code=status_code, cause=cause)
