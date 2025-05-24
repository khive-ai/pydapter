# Migration Guide: Transitioning from dev/ Directory

This guide is for users who have been using the experimental protocols and
migrations modules from the `dev/` directory. These modules have now been
integrated into the main package as optional dependencies.

## Overview of Changes

The protocols and migrations modules have been moved from the `dev/` directory
to the main package structure:

- `dev/protocols/` → `pydapter.protocols`
- `dev/migrations/` → `pydapter.migrations`

The functionality remains largely the same, but there are some important changes
to be aware of:

1. The modules are now optional dependencies
2. Import paths have changed
3. Backward compatibility is maintained temporarily
4. Type checking works regardless of installed dependencies

## Installation

To use the new modules, you need to install them as optional dependencies:

```bash
# For protocols module
pip install "pydapter[protocols]"

# For migrations core functionality
pip install "pydapter[migrations-core]"

# For SQL migrations with Alembic
pip install "pydapter[migrations-sql]"

# For all migrations components
pip install "pydapter[migrations]"

# For both protocols and migrations
pip install "pydapter[migrations-all]"

# For all pydapter features
pip install "pydapter[all]"
```

## Core System

The core adapter system remains unchanged in its API and functionality. The main
changes are related to import paths and enhanced error handling. If you're using
the core system directly, no code changes are required beyond updating import
statements.

## Fields System

The fields system has been integrated from the experimental `dev/` directory
with enhanced validation and protocol integration. Field definitions and usage
patterns remain the same, with improved type safety and documentation.

## Protocols and Fields

The protocols and fields systems now work together seamlessly, with protocols
leveraging pre-defined field definitions for consistency and reusability.

## Updating Import Statements

### Protocols Module

**Old imports:**

```python
from dev.protocols import Identifiable, Temporal, Embedable, Invokable, Event
from dev.protocols.types import Embedding, ExecutionStatus, Execution, Log
```

**New imports:**

```python
from pydapter.protocols import Identifiable, Temporal, Embedable, Invokable, Event
from pydapter.protocols import Embedding, ExecutionStatus, Execution, Log
```

### Migrations Module

**Old imports:**

```python
from dev.migrations import BaseMigrationAdapter, SyncMigrationAdapter, AsyncMigrationAdapter
from dev.migrations.protocols import MigrationProtocol, AsyncMigrationProtocol
from dev.migrations.exceptions import MigrationError
from dev.migrations.sql.alembic_adapter import AlembicAdapter, AsyncAlembicAdapter
```

**New imports:**

```python
from pydapter.migrations import BaseMigrationAdapter, SyncMigrationAdapter, AsyncMigrationAdapter
from pydapter.migrations import MigrationProtocol, AsyncMigrationProtocol
from pydapter.migrations import MigrationError
from pydapter.migrations import AlembicAdapter, AsyncAlembicAdapter
```

## Backward Compatibility

For a transitional period, the modules in the `dev/` directory will continue to
work by re-exporting from the new locations. However, you will see deprecation
warnings:

```text
DeprecationWarning: Importing from dev.protocols is deprecated and will be
removed in a future version. Please use pydapter.protocols instead.
```

It's recommended to update your import statements as soon as possible to avoid
issues when the backward compatibility is removed in a future version.

## Handling Missing Dependencies

If you try to import from the new modules without installing the required
dependencies, you'll get a clear error message:

```text
ImportError: The 'protocols' feature requires the 'typing_extensions' package.
Install it with: pip install pydapter[protocols]
```

This helps guide you to install the correct dependencies.

## Type Checking

The new modules are designed to work well with static type checkers like mypy,
even if the optional dependencies are not installed. This is achieved through
conditional imports with `TYPE_CHECKING`.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydapter.protocols import Identifiable, Temporal
```

## Examples

### Using Protocols

```python
# Old code
from dev.protocols import Identifiable, Temporal

class User(Identifiable, Temporal):
    name: str
    email: str

# New code
from pydapter.protocols import Identifiable, Temporal

class User(Identifiable, Temporal):
    name: str
    email: str
```

### Using Migrations

```python
# Old code
from dev.migrations.sql.alembic_adapter import AlembicAdapter

AlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb",
    models_module=models
)

# New code
from pydapter.migrations import AlembicAdapter

AlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb",
    models_module=models
)
```

## Troubleshooting

### Missing Dependencies

If you encounter import errors, make sure you've installed the required
dependencies:

```bash
pip install "pydapter[protocols]"
pip install "pydapter[migrations-sql]"
```

### Type Checking Issues

If you encounter type checking issues, make sure your type checker is configured
to handle conditional imports with `TYPE_CHECKING`. For mypy, this should work
out of the box.

### Circular Imports

If you encounter circular import errors, try using relative imports within your
modules:

```python
# Instead of
from pydapter.protocols import Identifiable

# Use
from ..protocols import Identifiable
```

## Timeline for Deprecation

The backward compatibility with the `dev/` directory will be maintained for at
least one minor version release. After that, the modules in the `dev/` directory
will be removed, and you'll need to use the new import paths.

## Additional Resources

- [Protocols Documentation](protocols.md)
- [Migrations Documentation](migrations.md)
- [Using Protocols Tutorial](tutorials/using_protocols.md)
- [Using Migrations Tutorial](tutorials/using_migrations.md)
