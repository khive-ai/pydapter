# Field to FieldTemplate Migration Guide

This guide explains how to migrate from the deprecated `Field` class to the new `FieldTemplate` system in pydapter.

## Overview

The `Field` class has been deprecated in favor of `FieldTemplate`, which provides a more compositional and flexible approach to defining fields. The new system uses method chaining for a cleaner API and better type safety.

## Key Changes

1. **Compositional API**: FieldTemplate uses method chaining instead of constructor parameters
2. **Immutable Design**: FieldTemplate instances are frozen dataclasses
3. **Better Caching**: Aggressive caching for performance with bounded memory usage
4. **Clearer Semantics**: Methods like `as_nullable()` and `with_default()` make intent clearer

## Migration Examples

### Basic Field Definition

**Old way (deprecated):**
```python
from pydapter.fields import Field

status_field = Field(
    name="status",
    annotation=str,
    default="active",
    description="Status of the record"
)
```

**New way:**
```python
from pydapter.fields import FieldTemplate

status_field = FieldTemplate(str).with_description("Status of the record").with_default("active")
```

### Nullable Fields

**Old way:**
```python
optional_field = Field(
    name="optional_field",
    annotation=str | None,
    default=None,
    description="Optional field"
)
```

**New way:**
```python
optional_field = FieldTemplate(str).with_description("Optional field").as_nullable()
# Note: as_nullable() automatically adds default=None if no default is specified
```

### Fields with Validators

**Old way:**
```python
def validate_positive(cls, v):
    if v < 0:
        raise ValueError("Must be positive")
    return v

age_field = Field(
    name="age",
    annotation=int,
    validator=validate_positive,
    description="Person's age"
)
```

**New way:**
```python
def validate_positive(v):  # Note: no 'cls' parameter
    if v < 0:
        raise ValueError("Must be positive")
    return v

age_field = FieldTemplate(int).with_description("Person's age").with_validator(validate_positive)
```

### Using with create_model

**Old way:**
```python
from pydapter.fields import Field, create_model

fields = [
    Field(name="id", annotation=UUID, default_factory=uuid4),
    Field(name="name", annotation=str, description="Name field"),
    Field(name="age", annotation=int, default=0)
]

MyModel = create_model("MyModel", fields=fields)
```

**New way:**
```python
from pydapter.fields import FieldTemplate, create_model
from pydapter.fields.common_templates import ID_TEMPLATE, NAME_TEMPLATE

fields = {
    "id": ID_TEMPLATE,
    "name": NAME_TEMPLATE,
    "age": FieldTemplate(int).with_description("Person's age").with_default(0)
}

MyModel = create_model("MyModel", fields=fields)
```

## Using Pre-built Templates

The new system provides many pre-built templates in `pydapter.fields.common_templates`:

```python
from pydapter.fields.common_templates import (
    ID_TEMPLATE,              # UUID field with default uuid4
    EMAIL_TEMPLATE,           # Email validation
    USERNAME_TEMPLATE,        # Username with pattern validation
    CREATED_AT_TEMPLATE,      # Creation timestamp
    UPDATED_AT_TEMPLATE,      # Update timestamp
    CREATED_AT_TZ_TEMPLATE,   # Timezone-aware creation timestamp
    UPDATED_AT_TZ_TEMPLATE,   # Timezone-aware update timestamp
    URL_TEMPLATE,             # URL validation
    PHONE_TEMPLATE,           # Phone number validation
    POSITIVE_INT_TEMPLATE,    # Positive integer
    PERCENTAGE_TEMPLATE,      # 0-100 float
    JSON_TEMPLATE,            # JSON/dict field
    TAGS_TEMPLATE,            # List of strings
    METADATA_TEMPLATE,        # Metadata dictionary
)
```

## Using Field Families

Field families group related fields together:

```python
from pydapter.fields import FieldFamilies, create_field_dict, create_model

# Create a model with entity fields (id, created_at, updated_at)
fields = create_field_dict(
    FieldFamilies.ENTITY_TZ,      # Timezone-aware timestamps
    FieldFamilies.SOFT_DELETE_TZ, # deleted_at, is_deleted
    FieldFamilies.AUDIT,          # created_by, updated_by, version
    # Add custom fields
    name=FieldTemplate(str).with_description("Entity name"),
    active=FieldTemplate(bool).with_default(True)
)

TrackedEntity = create_model("TrackedEntity", fields=fields)
```

## Using the DomainModelBuilder

The builder provides a fluent API for model creation:

```python
from pydapter.fields.builder import DomainModelBuilder

UserModel = (
    DomainModelBuilder("UserModel")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete(timezone_aware=True)
    .with_audit_fields()
    .add_field("username", FieldTemplate(str).with_description("Unique username"))
    .add_field("email", EMAIL_TEMPLATE)
    .add_field("is_active", FieldTemplate(bool).with_default(True))
    .build()
)
```

## Advanced Features

### List Fields

```python
# Old way
tags_field = Field(name="tags", annotation=list[str], default_factory=list)

# New way
tags_field = FieldTemplate(str).as_listable().with_description("Tags").with_default(list)
```

### Method Chaining

```python
# Complex field with multiple modifications
config_field = (
    FieldTemplate(dict)
    .with_description("Configuration settings")
    .with_default(dict)
    .as_nullable()
    .with_validator(lambda v: v if v is None or isinstance(v, dict) else None)
)
```

## Important Notes

1. **Validator signatures changed**: Validators now take only the value, not `cls` and value
2. **Nullable fields**: `as_nullable()` automatically adds `default=None` if no default is specified
3. **Field names**: When using `create_model` with a dict, field names come from the dict keys
4. **Backwards compatibility**: The old `Field` class still works but is deprecated

## Performance Considerations

The new FieldTemplate system includes:
- Bounded LRU cache for annotated types (configurable via `LIONAGI_FIELD_CACHE_SIZE` env var)
- Metadata limit warnings (configurable via `LIONAGI_FIELD_META_LIMIT` env var)
- Efficient type materialization with caching

## Full Example

```python
from datetime import datetime
from pydapter.fields import (
    FieldTemplate, 
    DomainModelBuilder,
    create_model,
    FieldFamilies,
    create_field_dict
)
from pydapter.fields.common_templates import EMAIL_TEMPLATE, USERNAME_TEMPLATE

# Method 1: Direct field definition
User = create_model(
    "User",
    fields={
        "id": FieldTemplate(UUID).with_default(uuid4),
        "username": USERNAME_TEMPLATE,
        "email": EMAIL_TEMPLATE,
        "age": FieldTemplate(int).with_validator(lambda v: v if v >= 0 else 0),
        "bio": FieldTemplate(str).as_nullable().with_description("User biography"),
        "created_at": FieldTemplate(datetime).with_default(datetime.utcnow)
    }
)

# Method 2: Using field families
BlogPost = create_model(
    "BlogPost",
    fields=create_field_dict(
        FieldFamilies.ENTITY_TZ,
        FieldFamilies.SOFT_DELETE_TZ,
        title=FieldTemplate(str).with_description("Post title"),
        content=FieldTemplate(str).with_description("Post content"),
        tags=FieldTemplate(str).as_listable().with_default(list),
        published=FieldTemplate(bool).with_default(False)
    )
)

# Method 3: Using the builder
Product = (
    DomainModelBuilder("Product")
    .with_entity_fields(timezone_aware=True)
    .add_field("name", FieldTemplate(str).with_description("Product name"))
    .add_field("price", FieldTemplate(float).with_validator(lambda v: v if v > 0 else 0))
    .add_field("in_stock", FieldTemplate(bool).with_default(True))
    .build()
)
```

For more examples, see `examples/new_field_template_usage.py`.