# Migrations API Reference

This page provides detailed API documentation for the `pydapter.migrations`
module.

## Installation

The migrations module is available as optional dependencies:

```bash
# Core migrations functionality
pip install "pydapter[migrations-core]"

# SQL migrations with Alembic support
pip install "pydapter[migrations-sql]"

# All migrations components
pip install "pydapter[migrations]"
```

## Module Overview

The migrations module provides a framework for managing database schema changes,
following the adapter pattern:

```text
MigrationProtocol
       │
       ▼
BaseMigrationAdapter
       │
       ├─────────────────────┐
       │                     │
       ▼                     ▼
SyncMigrationAdapter    AsyncMigrationAdapter
       │                     │
       ▼                     ▼
 AlembicAdapter        AsyncAlembicAdapter
```

## Protocols

### MigrationProtocol

::: pydapter.migrations.protocols.MigrationProtocol
    options:
      show_root_heading: true
      show_source: true

### AsyncMigrationProtocol

::: pydapter.migrations.protocols.AsyncMigrationProtocol
    options:
      show_root_heading: true
      show_source: true

## Base Classes

### BaseMigrationAdapter

::: pydapter.migrations.base.BaseMigrationAdapter
    options:
      show_root_heading: true
      show_source: true

### SyncMigrationAdapter

::: pydapter.migrations.base.SyncMigrationAdapter
    options:
      show_root_heading: true
      show_source: true

### AsyncMigrationAdapter

::: pydapter.migrations.base.AsyncMigrationAdapter
    options:
      show_root_heading: true
      show_source: true

## SQL Adapters

### AlembicAdapter

::: pydapter.migrations.sql.alembic_adapter.AlembicAdapter
    options:
      show_root_heading: true
      show_source: true

### AsyncAlembicAdapter

::: pydapter.migrations.sql.alembic_adapter.AsyncAlembicAdapter
    options:
      show_root_heading: true
      show_source: true

## Registry

::: pydapter.migrations.registry.MigrationRegistry
    options:
      show_root_heading: true
      show_source: true

## Exceptions

### MigrationError

::: pydapter.migrations.exceptions.MigrationError
    options:
      show_root_heading: true
      show_source: true

### MigrationInitError

::: pydapter.migrations.exceptions.MigrationInitError
    options:
      show_root_heading: true
      show_source: true

### MigrationCreationError

::: pydapter.migrations.exceptions.MigrationCreationError
    options:
      show_root_heading: true
      show_source: true

### MigrationUpgradeError

::: pydapter.migrations.exceptions.MigrationUpgradeError
    options:
      show_root_heading: true
      show_source: true

### MigrationDowngradeError

::: pydapter.migrations.exceptions.MigrationDowngradeError
    options:
      show_root_heading: true
      show_source: true

### MigrationNotFoundError

::: pydapter.migrations.exceptions.MigrationNotFoundError
    options:
      show_root_heading: true
      show_source: true
