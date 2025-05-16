"""
pydapter.migrations.exceptions - Custom exceptions for migration operations.
"""

from typing import Any, Optional

from pydapter.exceptions import AdapterError


class MigrationError(AdapterError):
    """Base exception for all migration-related errors."""

    def __init__(self, message: str, **context: Any):
        super().__init__(message, **context)


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
