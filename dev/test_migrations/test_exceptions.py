"""
Tests for migration-specific exceptions.
"""

import pytest

from pydapter.migrations.exceptions import (
    MigrationError,
    MigrationInitError,
    MigrationCreationError,
    MigrationUpgradeError,
    MigrationDowngradeError,
    MigrationNotFoundError,
)


def test_migration_error_base_class():
    """Test the base MigrationError class."""
    # Create a basic error
    error = MigrationError("Test migration error")
    assert str(error) == "Test migration error"
    
    # Create an error with context
    error = MigrationError("Test migration error", adapter="test", directory="/tmp/migrations")
    assert "Test migration error" in str(error)
    assert "adapter='test'" in str(error)
    assert "directory='/tmp/migrations'" in str(error)


def test_migration_init_error():
    """Test the MigrationInitError class."""
    error = MigrationInitError(
        "Failed to initialize migrations",
        directory="/tmp/migrations",
        adapter="test"
    )
    assert "Failed to initialize migrations" in str(error)
    assert "directory='/tmp/migrations'" in str(error)
    assert "adapter='test'" in str(error)


def test_migration_creation_error():
    """Test the MigrationCreationError class."""
    error = MigrationCreationError(
        "Failed to create migration",
        message_text="Test migration",
        autogenerate=True,
        adapter="test"
    )
    assert "Failed to create migration" in str(error)
    assert "message_text='Test migration'" in str(error)
    assert "autogenerate=True" in str(error)
    assert "adapter='test'" in str(error)


def test_migration_upgrade_error():
    """Test the MigrationUpgradeError class."""
    error = MigrationUpgradeError(
        "Failed to upgrade migrations",
        revision="head",
        adapter="test"
    )
    assert "Failed to upgrade migrations" in str(error)
    assert "revision='head'" in str(error)
    assert "adapter='test'" in str(error)


def test_migration_downgrade_error():
    """Test the MigrationDowngradeError class."""
    error = MigrationDowngradeError(
        "Failed to downgrade migrations",
        revision="abc123",
        adapter="test"
    )
    assert "Failed to downgrade migrations" in str(error)
    assert "revision='abc123'" in str(error)
    assert "adapter='test'" in str(error)


def test_migration_not_found_error():
    """Test the MigrationNotFoundError class."""
    error = MigrationNotFoundError(
        "Migration not found",
        revision="abc123",
        adapter="test"
    )
    assert "Migration not found" in str(error)
    assert "revision='abc123'" in str(error)
    assert "adapter='test'" in str(error)