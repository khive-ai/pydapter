# pydapter

[![PyPI version](https://badge.fury.io/py/pydapter.svg)](https://badge.fury.io/py/pydapter)
[![Python Versions](https://img.shields.io/pypi/pyversions/pydapter.svg)](https://pypi.org/project/pydapter/)
[![License](https://img.shields.io/github/license/agenticsorg/pydapter.svg)](https://github.com/agenticsorg/pydapter/blob/main/LICENSE)

**pydapter** is a powerful trait + adapter toolkit for pydantic models,
featuring a comprehensive field system and protocol-based design patterns.

## Overview

pydapter provides a lightweight, flexible way to adapt Pydantic models to
various data sources and sinks. It enables seamless data transfer between
different formats and storage systems while maintaining the type safety and
validation that Pydantic provides.

## ✨ Key Features

### 🏗️ **Field System** (New in v0.3.0)

- **Field Templates**: Reusable field definitions with flexible naming
- **Field Families**: Pre-defined collections for common patterns (Entity,
  Audit, Soft Delete)
- **Domain Model Builder**: Fluent API for composing models
- **Validation Patterns**: Built-in regex patterns and constraints

### 🔌 **Protocol System**

- **Type-Safe Constants**: Use `IDENTIFIABLE`, `TEMPORAL` instead of strings
- **Behavioral Mixins**: Add methods like `update_timestamp()` to your models
- **One-Step Creation**: `create_protocol_model_class()` for fields + behaviors

### 🔄 **Adapters**

- **Unified Interface**: Consistent API across different data sources
- **Type Safety**: Full Pydantic validation support
- **Async Support**: Both synchronous and asynchronous interfaces
- **Extensible**: Easy to create custom adapters

### 🚀 **Additional Features**

- **Migrations**: Database schema migration tools
- **Minimal Dependencies**: Core functionality has minimal requirements
- **Production Ready**: Battle-tested in real applications

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
pip install "pydapter[migrations-sql]" # Database schema migrations with
                                       # SQLAlchemy/Alembic

# Combined packages
pip install "pydapter[migrations]"     # All migration components
pip install "pydapter[migrations-all]" # Migrations with protocols support

# For all extras
pip install "pydapter[all]"
```

## Quick Examples

### 🏗️ Using the Field System

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate
from pydapter.protocols import (
    create_protocol_model_class,
    IDENTIFIABLE,
    TEMPORAL
)

# Build a model with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields(timezone_aware=True)  # id, created_at, updated_at
    .with_audit_fields()                      # created_by, updated_by, version
    .add_field("username", FieldTemplate(base_type=str, max_length=50))
    .add_field("email", FieldTemplate(base_type=str))
    .build()
)

# Or create a protocol-compliant model with behaviors
User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,  # Adds id field
    TEMPORAL,      # Adds created_at, updated_at fields + methods
    username=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str)
)

# Use the model
user = User(username="alice", email="alice@example.com")
user.update_timestamp()  # Method from TemporalMixin
```

### 🔄 Using Adapters

```python
from pydapter.adapters.json_ import JsonAdapter

# Create an adapter for your model
adapter = JsonAdapter[User](path="users.json")

# Read data
users = adapter.read_all()

# Write data
adapter.write_one(user)
```

## 📚 Documentation

### Getting Started

- 🚀 [**Getting Started Guide**](getting_started.md) - Your first steps with
  pydapter
- 🏗️ [**Field System Overview**](guides/fields.md) - Learn about the powerful
  field system
- 🔌 [**Protocols Overview**](protocols.md) - Understand protocol-based design

### Core Concepts

- 📋 [**Field Families**](guides/field-families.md) - Pre-built field
  collections
- 🎯 [**Best Practices**](guides/fields-and-protocols-patterns.md) - Field and
  protocol patterns
- ⚡ [**Error Handling**](error_handling.md) - Robust error management

### Tutorials & Guides

- 🔧 [**End-to-End Backend**](guides/end-to-end-backend.md) - Build a complete
  backend
- 📖 [**Using Protocols**](tutorials/using_protocols.md) - Protocol tutorial
- 🔄 [**Using Migrations**](tutorials/using_migrations.md) - Database migrations

### Adapters

- 🐘 [**PostgreSQL**](postgres_adapter.md) - PostgreSQL adapter guide
- 🔗 [**Neo4j**](neo4j_adapter.md) - Graph database integration
- 🔍 [**Qdrant**](qdrant_adapter.md) - Vector database support

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](contributing.md) for
details.

## 📄 License

pydapter is released under the Apache-2.0 License. See the
[LICENSE](https://github.com/agenticsorg/pydapter/blob/main/LICENSE) file for
details.
