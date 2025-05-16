# pydapter

[![PyPI version](https://badge.fury.io/py/pydapter.svg)](https://badge.fury.io/py/pydapter)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydapter.svg)](https://pypi.org/project/pydapter/)
[![License](https://img.shields.io/github/license/agenticsorg/pydapter.svg)](https://github.com/agenticsorg/pydapter/blob/main/LICENSE)
[![Tests](https://github.com/agenticsorg/pydapter/actions/workflows/tests.yml/badge.svg)](https://github.com/agenticsorg/pydapter/actions/workflows/tests.yml)

**pydapter** is a tiny trait + adapter toolkit for pydantic models.

## Overview

pydapter provides a lightweight, flexible way to adapt Pydantic models to
various data sources and sinks. It enables seamless data transfer between
different formats and storage systems while maintaining the type safety and
validation that Pydantic provides.

## Features

- **Unified Interface**: Consistent API for working with different data sources
- **Type Safety**: Leverages Pydantic's validation system
- **Extensible**: Easy to add new adapters for different data sources
- **Async Support**: Both synchronous and asynchronous interfaces
- **Minimal Dependencies**: Core functionality has minimal requirements
- **Protocols**: Optional standardized interfaces for models
- **Migrations**: Optional database schema migration tools

## Installation

```bash
pip install pydapter
```

With optional dependencies:

```bash
# Database adapters
pip install "pydapter[postgres]"
pip install "pydapter[mongo]"
pip install "pydapter[neo4j]"

# File formats
pip install "pydapter[excel]"

# New modules
pip install "pydapter[protocols]"      # Standardized model interfaces
pip install "pydapter[migrations-sql]" # Database schema migrations with SQLAlchemy/Alembic

# Combined packages
pip install "pydapter[migrations]"     # All migration components
pip install "pydapter[migrations-all]" # Migrations with protocols support

# For all extras
pip install "pydapter[all]"
```

## Quick Example

```python
from pydantic import BaseModel
from typing import List
from pydapter.adapters.json_ import JsonAdapter

# Define your model
class User(BaseModel):
    id: int
    name: str
    email: str

# Create an adapter
adapter = JsonAdapter[User](path="users.json")

# Read data
users: List[User] = adapter.read_all()

# Write data
new_user = User(id=3, name="Alice", email="alice@example.com")
adapter.write_one(new_user)
```

## Next Steps

- Check out the [Getting Started](getting_started.md) guide
- Learn about [Error Handling](error_handling.md)
- Explore specific adapters like [PostgreSQL](postgres_adapter.md),
  [Neo4j](neo4j_adapter.md), or [Qdrant](qdrant_adapter.md)
- Use [Protocols](protocols.md) to add standardized capabilities to your models
- Manage database schema changes with [Migrations](migrations.md)
- Follow our tutorials:
  - [Using Protocols](tutorials/using_protocols.md)
  - [Using Migrations](tutorials/using_migrations.md)
- If you're transitioning from the dev/ directory, see the
  [Migration Guide](migration_guide.md)
