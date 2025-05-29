# Working with Pydapter Fields

## Field System Overview

Pydapter provides a comprehensive field system built on top of Pydantic v2 that includes:

- **Field Templates**: Reusable field definitions with flexible naming
- **Common Templates**: Pre-configured templates for common field types
  (IDs, timestamps, etc.)
- **Field Families**: Logical groupings of fields for database patterns
- **Protocol Families**: Field sets that match pydapter protocol requirements
- **Validation Patterns**: Common regex patterns and constraint builders
- **Domain Model Builder**: Fluent API for creating models

## Field Templates

Field templates are reusable field definitions that can be customized for different contexts:

```python
from pydapter.fields import FieldTemplate

# Define a reusable template
name_template = FieldTemplate(
    base_type=str,
    description="Name field",
    min_length=1,
    max_length=100
)

# Use in models with different field names
from pydapter.fields import create_model

User = create_model(
    "User",
    fields={
        "username": name_template.create_field("username"),
        "full_name": name_template.create_field("full_name")
    }
)
```

## Common Field Templates

Pydapter provides pre-configured templates for common field types:

```python
from pydapter.fields import (
    ID_TEMPLATE,
    CREATED_AT_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    EMAIL_TEMPLATE,
    URL_TEMPLATE,
    JSON_TEMPLATE,
    TAGS_TEMPLATE
)

# Using templates in model creation
fields = {
    "id": ID_TEMPLATE.create_field("id"),
    "email": EMAIL_TEMPLATE.create_field("email"),
    "website": URL_TEMPLATE.create_field("website"),
    "tags": TAGS_TEMPLATE.create_field("tags")
}

User = create_model("User", fields=fields)
```

## Field Families

Field families are logical groupings of fields for common database patterns:

```python
from pydapter.fields import FieldFamilies, create_field_dict, create_model

# Core families available:
# - ENTITY: id, created_at, updated_at
# - ENTITY_TZ: Same but with timezone-aware timestamps
# - SOFT_DELETE: deleted_at, is_deleted
# - AUDIT: created_by, updated_by, version

# Combine families to create models
fields = create_field_dict(
    FieldFamilies.ENTITY,
    FieldFamilies.AUDIT,
    FieldFamilies.SOFT_DELETE
)

AuditedEntity = create_model("AuditedEntity", fields=fields)
```

## Domain Model Builder

The DomainModelBuilder provides a fluent API for creating models:

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

# Build a model with method chaining
TrackedEntity = (
    DomainModelBuilder("TrackedEntity")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete(timezone_aware=True)
    .with_audit_fields()
    .add_field("name", FieldTemplate(
        base_type=str,
        description="Entity name",
        max_length=100
    ))
    .add_field("status", FieldTemplate(
        base_type=str,
        default="active",
        description="Entity status"
    ))
    .build()
)
```

## Protocol Field Families

For models that need to implement pydapter protocols:

```python
from pydapter.fields import create_protocol_model, FieldTemplate

# Create a model implementing multiple protocols
Document = create_protocol_model(
    "Document",
    "identifiable",    # Adds id field
    "temporal",        # Adds created_at, updated_at
    "embeddable",      # Adds embedding field
    "cryptographical", # Adds sha256 field
    timezone_aware=True,
    # Add custom fields
    title=FieldTemplate(base_type=str, description="Document title"),
    content=FieldTemplate(base_type=str, description="Document content")
)
```

## Validation Patterns

Use pre-built validation patterns for common field types:

```python
from pydapter.fields import (
    ValidationPatterns,
    create_pattern_template,
    create_range_template
)

# Use pre-defined patterns
slug_field = create_pattern_template(
    ValidationPatterns.SLUG,
    description="URL-friendly slug",
    error_message="Must contain only lowercase letters, numbers, and hyphens"
)

phone_field = create_pattern_template(
    ValidationPatterns.US_PHONE,
    description="US phone number"
)

# Create range-constrained fields
percentage = create_range_template(
    float,
    ge=0,
    le=100,
    description="Percentage value"
)

age = create_range_template(
    int,
    ge=0,
    le=150,
    description="Person's age"
)
```

## Field Template Modifiers

Field templates support transformation methods:

```python
from pydapter.fields import ID_TEMPLATE, EMAIL_TEMPLATE

# Make fields nullable
nullable_id = ID_TEMPLATE.as_nullable()
optional_email = EMAIL_TEMPLATE.as_nullable()

# Copy with modifications
custom_id = ID_TEMPLATE.copy(
    description="Custom identifier",
    frozen=False  # Make it mutable
)

# Change field properties
long_description = FieldTemplate(
    base_type=str,
    max_length=1000
).copy(max_length=2000)
```

## Complete Example

Here's a comprehensive example combining the field system features:

```python
from pydapter.fields import (
    DomainModelBuilder,
    FieldTemplate,
    create_protocol_model,
    create_pattern_template,
    ValidationPatterns
)

# 1. Using DomainModelBuilder
BlogPost = (
    DomainModelBuilder("BlogPost")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete()
    .with_audit_fields()
    .add_field("title", FieldTemplate(
        base_type=str,
        description="Post title",
        max_length=200
    ))
    .add_field("slug", create_pattern_template(
        ValidationPatterns.SLUG,
        description="URL slug"
    ))
    .add_field("content", FieldTemplate(
        base_type=str,
        description="Post content"
    ))
    .build()
)

# 2. Using Protocol Models
EmbeddableDocument = create_protocol_model(
    "EmbeddableDocument",
    "identifiable",
    "temporal",
    "embeddable",
    title=FieldTemplate(base_type=str),
    content=FieldTemplate(base_type=str),
    tags=FieldTemplate(
        base_type=list[str],
        default_factory=list
    )
)

# 3. Custom field family
custom_family = {
    "name": FieldTemplate(base_type=str, max_length=100),
    "email": EMAIL_TEMPLATE,
    "is_active": FieldTemplate(base_type=bool, default=True)
}

CustomModel = (
    DomainModelBuilder("CustomModel")
    .with_entity_fields()
    .with_family(custom_family)
    .build()
)
```

## Key Design Principles

1. **Templates over instances**: Field templates can be reused across multiple fields
2. **Composition over inheritance**: Build complex models by combining families
3. **Protocol alignment**: Use protocol families for models that implement
   pydapter protocols
4. **Validation patterns**: Leverage pre-built patterns for common validation needs
5. **Fluent API**: Use method chaining for readable model construction

The field system provides a foundation for creating consistent, validated data
models that integrate seamlessly with pydapter's adapter ecosystem.
