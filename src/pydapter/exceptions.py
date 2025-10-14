"""
pydapter.exceptions - Custom exception hierarchy for pydapter.
"""

from __future__ import annotations

from typing import Any

from .types import BaseError

PYDAPTER_PYTHON_ERRORS = (KeyError, ImportError, AttributeError, ValueError)


__all__ = (
    "PydapterError",
    "ValidationError",
    "TypeConversionError",
    "ParseError",
    "ConnectionError",
    "QueryError",
    "ResourceError",
    "ConfigurationError",
    "AdapterNotFoundError",
    "AdapterError",  # backward compatibility alias
    "PYDAPTER_PYTHON_ERRORS",
)


class PydapterError(BaseError):
    """Base exception for all pydapter errors."""

    default_message = "Pydapter error"
    default_status_code = 500
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        adapter: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        if adapter:
            details["adapter"] = adapter
        # Merge any extra kwargs into details
        details.update(extra_context)
        super().__init__(message, details=details, status_code=status_code, cause=cause)


# Error classes
class ValidationError(PydapterError):
    """Exception raised when data validation fails."""

    default_message = "Validation failed"
    default_status_code = 422  # Unprocessable Entity
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        data: Any | None = None,
        errors: list[dict] | None = None,
        field_path: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "data": data,
            "errors": errors,
            "field_path": field_path,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class TypeConversionError(ValidationError):
    """Exception raised when type conversion fails."""

    default_message = "Type conversion failed"
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        source_type: type | None = None,
        target_type: type | None = None,
        field_name: str | None = None,
        model_name: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        # Always include source_type and target_type (even if None) for attribute access
        details["source_type"] = source_type
        details["target_type"] = target_type
        # Store string names for serialization (only if type is not None)
        if source_type:
            details["source_type_name"] = source_type.__name__
        if target_type:
            details["target_type_name"] = target_type.__name__
        # Add other optional fields
        params = {
            "field_name": field_name,
            "model_name": model_name,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)

        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class ParseError(PydapterError):
    """Exception raised when data parsing fails."""

    default_message = "Parse failed"
    default_status_code = 400  # Bad Request
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        source: str | None = None,
        position: int | None = None,
        line: int | None = None,
        column: int | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "source": source,
            "position": position,
            "line": line,
            "column": column,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class ConnectionError(PydapterError):
    """Exception raised when a connection to a data source fails."""

    default_message = "Connection failed"
    default_status_code = 503  # Service Unavailable
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        url: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "url": url,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class QueryError(PydapterError):
    """Exception raised when a query to a data source fails."""

    default_message = "Query failed"
    default_status_code = 400  # Bad Request
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        query: Any | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "query": query,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class ResourceError(PydapterError):
    """Exception raised when a resource (file, database, etc.) cannot be accessed."""

    default_message = "Resource not found"
    default_status_code = 404  # Not Found
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        resource: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "resource": resource,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class ConfigurationError(PydapterError):
    """Exception raised when adapter configuration is invalid."""

    default_message = "Configuration invalid"
    default_status_code = 500  # Internal Server Error
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        config: dict[str, Any] | None = None,
        adapter_class: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "config": config,
            "adapter_class": adapter_class,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


class AdapterNotFoundError(PydapterError):
    """Exception raised when an adapter is not found."""

    default_message = "Adapter not found"
    default_status_code = 404  # Not Found
    __slots__ = ()

    def __init__(
        self,
        message: str | None = None,
        *,
        obj_key: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        adapter: str | None = None,
        **extra_context: Any,
    ):
        details = details or {}
        params = {
            "obj_key": obj_key,
        }
        details.update({k: v for k, v in params.items() if v is not None})
        details.update(extra_context)
        super().__init__(
            message,
            details=details,
            status_code=status_code,
            cause=cause,
            adapter=adapter,
        )


# Backward compatibility alias
AdapterError = PydapterError
