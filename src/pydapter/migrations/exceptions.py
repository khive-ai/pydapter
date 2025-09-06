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
        super().__init__(message, **context)
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
        super().__init__(message, directory=directory, adapter=adapter, **context)
        self.directory = directory
        self.adapter = adapter
        # Ensure original_error is set even if not passed through super().__init__
        if "original_error" in context:
            self.original_error = context["original_error"]


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
        super().__init__(
            message,
            message_text=message_text,
            autogenerate=autogenerate,
            adapter=adapter,
            **context,
        )
        self.message_text = message_text
        self.autogenerate = autogenerate
        self.adapter = adapter
        # Ensure original_error is set even if not passed through super().__init__
        if "original_error" in context:
            self.original_error = context["original_error"]


class MigrationUpgradeError(MigrationError):
    """Exception raised when migration upgrade fails."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, revision=revision, adapter=adapter, **context)
        self.revision = revision
        self.adapter = adapter
        # Ensure original_error is set even if not passed through super().__init__
        if "original_error" in context:
            self.original_error = context["original_error"]


class MigrationDowngradeError(MigrationError):
    """Exception raised when migration downgrade fails."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, revision=revision, adapter=adapter, **context)
        self.revision = revision
        self.adapter = adapter
        # Ensure original_error is set even if not passed through super().__init__
        if "original_error" in context:
            self.original_error = context["original_error"]


class MigrationNotFoundError(MigrationError):
    """Exception raised when a migration is not found."""

    def __init__(
        self,
        message: str,
        revision: Optional[str] = None,
        adapter: Optional[str] = None,
        **context: Any,
    ):
        super().__init__(message, revision=revision, adapter=adapter, **context)
        self.revision = revision
        self.adapter = adapter
        # Ensure original_error is set even if not passed through super().__init__
        if "original_error" in context:
            self.original_error = context["original_error"]
