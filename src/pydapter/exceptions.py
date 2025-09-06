"""
pydapter.exceptions - Structured exception hierarchy for pydapter.

Based on lionagi error pattern with rich context, exception chaining, and status codes.
"""

from __future__ import annotations

from typing import Any, ClassVar

from .utils import truncate_for_display

PYDAPTER_PYTHON_ERRORS = (KeyError, ImportError, AttributeError, ValueError)

__all__ = (
    "PYDAPTER_PYTHON_ERRORS",
    "PydapterError",
    "ValidationError",
    "ParseError",
    "ConnectionError",
    "QueryError",
    "ResourceError",
    "ConfigurationError",
    "AdapterNotFoundError",
    "TypeConversionError",
    "AdapterError",  # Legacy aliases
)


class PydapterError(Exception):
    """Base exception for all pydapter errors."""

    default_message: ClassVar[str] = "Pydapter error"
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

    def to_dict(self, *, include_cause: bool = False) -> dict[str, Any]:
        """Convert error to structured dictionary."""
        data = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            **({**self.details} if self.details else {}),
        }
        if include_cause and (cause := self.get_cause()):
            data["cause"] = repr(cause)
        return data

    def get_cause(self) -> Exception | None:
        """Get the cause of this error, if any."""
        return self.__cause__ if hasattr(self, "__cause__") else None

    @classmethod
    def from_value(
        cls,
        value: Any,
        message: str | None = None,
        *,
        expected: str | None = None,
        cause: Exception | None = None,
        **extra: Any,
    ):
        """Create error from a value with optional expected type and message."""
        details = {
            "value": value,
            "type": type(value).__name__,
            **({**{"expected": expected}} if expected else {}),
            **extra,
        }
        return cls(message=message, details=details, cause=cause)

    @classmethod
    def from_adapter(
        cls,
        adapter_cls: type,
        message: str | None = None,
        cause: Exception | None = None,
        **extra: Any,
    ):
        obj_key = getattr(adapter_cls, "obj_key", None)
        if not obj_key:
            raise ValueError("Adapter class must have an 'obj_key' attribute")

        # Auto-truncate 'source' if present in extra
        if "source" in extra:
            extra["source"] = truncate_for_display(extra["source"])

        details = {"adapter_obj_key": obj_key, **extra}
        return cls(message=message, details=details, cause=cause)


class ValidationError(PydapterError):
    """Exception raised when data validation fails."""

    default_message = "Data validation failed"
    default_status_code = 422
    __slots__ = ()


class ParseError(PydapterError):
    """Exception raised when data parsing fails."""

    default_message = "Data parsing failed"
    default_status_code = 400
    __slots__ = ()


class ConnectionError(PydapterError):
    """Exception raised when a connection to a data source fails."""

    default_message = "Connection failed"
    default_status_code = 503
    __slots__ = ()


class QueryError(PydapterError):
    """Exception raised when a query to a data source fails."""

    default_message = "Query failed"
    default_status_code = 400
    __slots__ = ()


class ResourceError(PydapterError):
    """Exception raised when a resource cannot be accessed."""

    default_message = "Resource access failed"
    default_status_code = 404
    __slots__ = ()


class ConfigurationError(PydapterError):
    """Exception raised when adapter configuration is invalid."""

    default_message = "Configuration error"
    default_status_code = 422
    __slots__ = ()


class AdapterNotFoundError(PydapterError):
    """Exception raised when an adapter is not found."""

    default_message = "Adapter not found"
    default_status_code = 404
    __slots__ = ()


class TypeConversionError(ValidationError):
    """Exception raised when type conversion fails."""

    default_message = "Type conversion failed"
    default_status_code = 422
    __slots__ = ()


# Legacy alias for backward compatibility
AdapterError = PydapterError
