"""
pydapter.migrations.exceptions - Custom exceptions for migration operations.
"""

from typing import Any, Optional

from pydapter.exceptions import AdapterError


class MigrationError(AdapterError):
    """Base exception for all migration-related errors."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert old-style arguments to new details format
        details = context.copy()
        if adapter is not None:
            details["adapter"] = adapter
        if original_error is not None:
            details["original_error"] = str(original_error)

        # Only use cause if original_error is actually an exception
        cause = original_error if isinstance(original_error, BaseException) else None
        super().__init__(message, details=details, cause=cause)
        self.original_error = original_error
        self.adapter = adapter

    def __str__(self) -> str:
        """Return a string representation of the error."""
        result = super().__str__()
        if hasattr(self, "original_error") and self.original_error is not None:
            result += f" (original_error='{self.original_error}')"
        return result


class MigrationInitError(MigrationError):
    """Exception raised when migration initialization fails."""

    def __init__(
        self,
        message: str,
        directory: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert to new exception pattern
        super().__init__(message, adapter=adapter, **context)
        self.directory = directory


class MigrationCreationError(MigrationError):
    """Exception raised when migration creation fails."""

    def __init__(
        self,
        message: str,
        message_text: Optional[str] = None,
        autogenerate: Optional[bool] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert to new exception pattern
        super().__init__(message, adapter=adapter, **context)
        self.message_text = message_text
        self.autogenerate = autogenerate


class MigrationUpgradeError(MigrationError):
    """Exception raised when migration upgrade fails."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert to new exception pattern
        super().__init__(message, adapter=adapter, **context)
        self.revision = revision


class MigrationDowngradeError(MigrationError):
    """Exception raised when migration downgrade fails."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert to new exception pattern
        super().__init__(message, adapter=adapter, **context)
        self.revision = revision


class MigrationNotFoundError(MigrationError):
    """Exception raised when a migration is not found."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        # Convert to new exception pattern
        super().__init__(message, adapter=adapter, **context)
        self.revision = revision
