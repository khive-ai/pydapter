# Fields API Reference

This page provides API documentation for the `pydapter.fields` module.

## Installation

```bash
pip install pydapter
```

## Overview

The fields module provides tools for building robust, reusable model definitions:

```text
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│      Field      │  │  FieldTemplate  │  │  FieldFamilies  │
│  (Descriptor)   │  │   (Reusable)    │  │   (Collections) │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│DomainModelBuilder│  │ValidationPatterns│
│   (Fluent API)  │  │   (Validators)  │
└─────────────────┘  └─────────────────┘
```

## Quick Start

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

# Build models with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields()                    # id, created_at, updated_at
    .with_audit_fields()                     # created_by, updated_by, version
    .add_field("name", FieldTemplate(base_type=str))
    .add_field("email", FieldTemplate(base_type=str))
    .build()
)
```

## Field Templates

```python
from pydapter.fields import FieldTemplate

# Reusable field configuration
email_template = FieldTemplate(
    base_type=str,
    description="Email address",
    validator=lambda cls, v: v.lower()
)

# Create variations
user_email = email_template.create_field("user_email")
optional_email = email_template.as_nullable()
email_list = email_template.as_listable()
```

## Field Families

```python
from pydapter.fields import FieldFamilies

# Pre-defined collections
entity_fields = FieldFamilies.ENTITY        # id, created_at, updated_at
audit_fields = FieldFamilies.AUDIT          # created_by, updated_by, version
soft_delete_fields = FieldFamilies.SOFT_DELETE  # deleted_at, is_deleted
```

## Model Creation

```python
from pydapter.fields import create_model, Field

# Create models with field lists
fields = [
    Field(name="id", annotation=str),
    Field(name="name", annotation=str),
    Field(name="email", annotation=str)
]

User = create_model("User", fields=fields)
```

---

## API Reference

### Core Types

::: pydapter.fields.types
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.template
    options:
      show_root_heading: true
      show_source: true

### Specialized Fields

::: pydapter.fields.ids
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.dts
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.embedding
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.execution
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.params
    options:
      show_root_heading: true
      show_source: true

### Field Collections

::: pydapter.fields.common_templates
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.families
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.protocol_families
    options:
      show_root_heading: true
      show_source: true

### Builders and Utilities

::: pydapter.fields.builder
    options:
      show_root_heading: true
      show_source: true

::: pydapter.fields.validation_patterns
    options:
      show_root_heading: true
      show_source: true
