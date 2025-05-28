# Working with Pydapter Fields

## Field System Overview

Pydapter extends Pydantic fields with:

- Advanced descriptors
- Composition methods (`as_nullable()`, `as_listable()`)
- Pre-configured fields for common patterns
- Metadata for adapter integration

## Core Field Class

```python
from pydapter.fields import Field

# Basic field definition
name_field = Field(
    name="name",
    annotation=str,
    description="User's full name",
    validator=lambda cls, v: v.strip() if v else v
)
```

## Pre-configured Fields

### Essential Fields

- **`ID_FROZEN`**: Immutable UUID field
- **`ID_NULLABLE`**: Optional UUID field
- **`DATETIME`**: Timezone-aware datetime with ISO serialization
- **`DATETIME_NULLABLE`**: Optional datetime field
- **`EMBEDDING`**: Vector embedding field with validation
- **`EXECUTION`**: Execution tracking field

### Usage Pattern

```python
from pydapter.fields import ID_FROZEN, DATETIME, EMBEDDING

class Document(BaseModel):
    id: UUID = ID_FROZEN.field_info
    created_at: datetime = DATETIME.field_info
    embedding: list[float] = EMBEDDING.field_info
```

## Field Composition

### Nullable Transformation

```python
email_field = Field(name="email", annotation=str, validator=validate_email)
optional_email = email_field.as_nullable()

class User(BaseModel):
    email: str = email_field.field_info
    backup_email: str | None = optional_email.field_info
```

### List Transformation

```python
tag_field = Field(name="tag", annotation=str, validator=lambda cls, v: v.lower())
tags_field = tag_field.as_listable()          # Accepts single value or list
strict_tags = tag_field.as_listable(strict=True)  # Only accepts lists
```

## Custom Field Patterns

### Domain-Specific Fields

```python
CURRENCY_AMOUNT = Field(
    name="amount",
    annotation=Decimal,
    validator=lambda cls, v: validate_positive_decimal(v),
    description="Positive currency amount",
    json_schema_extra={"format": "decimal", "multipleOf": 0.01}
)

PERCENTAGE = Field(
    name="percentage",
    annotation=float,
    validator=lambda cls, v: max(0.0, min(100.0, float(v))),
    json_schema_extra={"minimum": 0, "maximum": 100}
)
```

### Field Families

```python
# Base field
EMAIL_BASE = Field(name="email", annotation=str, validator=validate_email)

# Variations
EMAIL_REQUIRED = EMAIL_BASE
EMAIL_OPTIONAL = EMAIL_BASE.as_nullable()
EMAIL_LIST = EMAIL_BASE.as_listable()
```

## Adapter Integration

### Metadata for Database Adapters

```python
VECTOR_FIELD = Field(
    name="embedding",
    annotation=list[float],
    json_schema_extra={
        "vector_dim": 768,
        "distance_metric": "cosine",
        "db_index_type": "hnsw"
    }
)

USERNAME_FIELD = Field(
    name="username",
    annotation=str,
    json_schema_extra={
        "db_index": True,
        "db_unique": True,
        "db_column": "user_name"
    }
)
```

### Accessing Field Metadata

```python
def create_table_schema(model_class):
    for field_name, field_info in model_class.model_fields.items():
        extra = field_info.json_schema_extra or {}
        
        if extra.get("db_index"):
            print(f"CREATE INDEX ON {field_name}")
        if extra.get("vector_dim"):
            print(f"CREATE VECTOR COLUMN dimension={extra['vector_dim']}")
```

## Dynamic Field Creation

```python
def create_string_field(name: str, max_length: int = None):
    """Factory for string fields with optional length validation"""
    validator = lambda cls, v: v[:max_length] if max_length and v else v
    
    return Field(
        name=name,
        annotation=str,
        validator=validator if max_length else None,
        json_schema_extra={"maxLength": max_length} if max_length else {}
    )

# Usage
title_field = create_string_field("title", max_length=100)
description_field = create_string_field("description", max_length=500)
```

## Key Tips for LLM Developers

### 1. Field Reuse Strategy

```python
# Create fields module for your domain
# fields.py
USER_ID = ID_FROZEN.copy(name="user_id")
CREATED_AT = DATETIME.copy(name="created_at")
PRICE = Field(name="price", annotation=Decimal, validator=validate_positive)

# Use across models
class User(BaseModel):
    id: UUID = USER_ID.field_info
    created_at: datetime = CREATED_AT.field_info

class Order(BaseModel):
    id: UUID = ID_FROZEN.field_info  # or create ORDER_ID variant
    user_id: UUID = USER_ID.field_info
    total: Decimal = PRICE.field_info
```

### 2. Composition Over Duplication

```python
# Base field
BASE_TEXT = Field(name="text", annotation=str, validator=lambda cls, v: v.strip())

# Composed variations
TITLE = BASE_TEXT.copy(name="title", description="Title text")
OPTIONAL_DESCRIPTION = BASE_TEXT.copy(name="description").as_nullable()
TAG_LIST = BASE_TEXT.as_listable(strict=True)
```

### 3. Validation Patterns

```python
def validate_email(cls, v):
    if v and "@" not in v:
        raise ValueError("Invalid email format")
    return v

def validate_positive(cls, v):
    if v is not None and v < 0:
        raise ValueError("Must be positive")
    return v
```

### 4. Testing Field Behavior

```python
def test_field_composition():
    base = Field(name="test", annotation=str)
    nullable = base.as_nullable()
    listable = base.as_listable()
    
    assert nullable.annotation != base.annotation  # Should be Union[str, None]
    assert base.name == nullable.name == listable.name
```

### 5. Common Caveats

- **Field copying**: Use `.copy()` to avoid modifying original fields
- **Validator scope**: Validators receive `(cls, value)`, not just `value`
- **Composition order**: `as_nullable().as_listable()` vs
  `as_listable().as_nullable()`
- **Metadata inheritance**: `json_schema_extra` is preserved through composition

### 6. Integration with Protocols

```python
class StandardEntity(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID = ID_FROZEN.field_info
    created_at: datetime = DATETIME.field_info
    updated_at: datetime = DATETIME.field_info
```

The field system provides a powerful foundation for creating reusable, validated
field definitions that integrate seamlessly with pydapter's adapter ecosystem.
