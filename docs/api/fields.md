# Fields API Reference

This page provides detailed API documentation for the `pydapter.fields` module, which
implements a robust system for defining and managing data fields with enhanced
validation, type transformation, and protocol integration.

## Installation

```bash
pip install pydapter
```

## Module Overview

The fields module extends Pydantic's field system with additional features for
building robust, reusable model definitions:

```text
Fields Architecture:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│      Field      │  │  FieldTemplate  │  │  FieldFamilies  │
│  (Descriptor)   │  │   (Reusable)    │  │   (Collections) │
│                 │  │                 │  │                 │
│ name            │  │ base_type       │  │ ENTITY          │
│ annotation      │  │ as_nullable()   │  │ SOFT_DELETE     │
│ validator       │  │ as_listable()   │  │ AUDIT           │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│DomainModelBuilder│  │ValidationPatterns│ │ProtocolFieldFam │
│   (Fluent API)  │  │   (Validators)  │  │  (Protocol Map) │
│                 │  │                 │  │                 │
│ with_entity()   │  │ EMAIL           │  │ IDENTIFIABLE    │
│ with_audit()    │  │ URL             │  │ TEMPORAL        │
│ build()         │  │ PHONE           │  │ EMBEDDABLE      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

The system provides:

- **Enhanced Field Descriptors**: More powerful than standard Pydantic fields
- **Field Templates**: Reusable field configurations with composition methods
- **Field Families**: Pre-defined collections for common patterns
- **Domain Builder**: Fluent API for model creation
- **Protocol Integration**: Seamless integration with pydapter protocols

## Core Components

### Field and FieldTemplate System

```python
from pydapter.fields import Field, FieldTemplate

# Field: Basic descriptor for individual fields
name_field = Field(
    name="name",
    annotation=str,
    description="User's full name",
    validator=lambda cls, v: v.strip().title()
)

# FieldTemplate: Reusable configuration that can be applied to different names
email_template = FieldTemplate(
    base_type=str,
    description="Email address",
    validator=lambda cls, v: v.lower()
)

# Use template to create fields with different names
user_email = email_template.create_field("user_email")
contact_email = email_template.create_field("contact_email")

# Create variations
optional_email = email_template.as_nullable()
email_list = email_template.as_listable()
```

### Domain Model Builder

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

# Fluent API for building models with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields(timezone_aware=True)     # id, created_at, updated_at
    .with_audit_fields()                         # created_by, updated_by, version
    .with_soft_delete(timezone_aware=True)       # deleted_at, is_deleted
    .add_field("name", FieldTemplate(base_type=str))
    .add_field("email", FieldTemplate(base_type=str))
    .build()
)
```

### Field Families

```python
from pydapter.fields import FieldFamilies

# Pre-defined field collections for common patterns
entity_fields = FieldFamilies.ENTITY        # id, created_at, updated_at
entity_tz_fields = FieldFamilies.ENTITY_TZ  # timezone-aware timestamps
soft_delete_fields = FieldFamilies.SOFT_DELETE  # deleted_at, is_deleted
audit_fields = FieldFamilies.AUDIT          # created_by, updated_by, version
```

### Protocol Field Families

```python
from pydapter.fields import ProtocolFieldFamilies

# Protocol-specific field collections
identifiable_fields = ProtocolFieldFamilies.IDENTIFIABLE  # id field
temporal_fields = ProtocolFieldFamilies.TEMPORAL          # timestamps
embeddable_fields = ProtocolFieldFamilies.EMBEDDABLE      # content, embedding
auditable_fields = ProtocolFieldFamilies.AUDITABLE        # audit tracking
```

### Pre-defined Field Templates

```python
from pydapter.fields import (
    ID_TEMPLATE,
    STRING_TEMPLATE,
    EMAIL_TEMPLATE,
    CREATED_AT_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    JSON_TEMPLATE,
    METADATA_TEMPLATE
)

# Use pre-defined templates
user_id = ID_TEMPLATE.create_field("user_id")
user_name = STRING_TEMPLATE.create_field("name")
user_email = EMAIL_TEMPLATE.create_field("email")
```

## Type Definitions

```python
from pydapter.fields import ID, Embedding, Metadata, Undefined

# Type aliases for common field types
ID = uuid.UUID           # UUID type alias
Embedding = list[float]  # Vector embedding type
Metadata = dict         # Metadata dictionary type
Undefined              # Sentinel for undefined values
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

# With field families
from pydapter.fields import create_field_dict, FieldFamilies

# Combine field families
all_fields = {
    **FieldFamilies.ENTITY,
    **FieldFamilies.AUDIT,
    "name": FieldTemplate(base_type=str),
    "email": FieldTemplate(base_type=str)
}

field_dict = create_field_dict(all_fields)
TrackedUser = create_model("TrackedUser", fields=field_dict)
```

## Validation Patterns

```python
from pydapter.fields import ValidationPatterns, create_pattern_template, create_range_template

# Use pre-defined validation patterns
email_field = create_pattern_template(
    "email",
    ValidationPatterns.EMAIL,
    "Valid email address"
)

age_field = create_range_template(
    "age",
    min_val=0,
    max_val=150,
    description="Age in years"
)
```

## Advanced Usage

### Custom Field Templates

```python
from pydapter.fields import FieldTemplate

# Create reusable field template with validation
price_template = FieldTemplate(
    base_type=float,
    description="Price in USD",
    validator=lambda cls, v: round(max(0, v), 2),  # Positive, 2 decimals
    json_schema_extra={"minimum": 0, "multipleOf": 0.01}
)

# Use in multiple contexts
product_price = price_template.create_field("price")
shipping_cost = price_template.create_field("shipping_cost")
tax_amount = price_template.create_field("tax_amount")
```

### Protocol Integration

```python
from pydapter.fields import ProtocolFieldFamilies, create_protocol_model
from pydapter.protocols.constants import IDENTIFIABLE, TEMPORAL

# Create protocol-compliant model using field families
User = create_protocol_model(
    "User",
    IDENTIFIABLE,
    TEMPORAL,
    name=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str)
)
```

### Model Builder Patterns

```python
# Pattern 1: Basic entity
BasicEntity = (
    DomainModelBuilder("BasicEntity")
    .with_entity_fields()
    .add_field("name", FieldTemplate(base_type=str))
    .build()
)

# Pattern 2: Tracked entity with audit
TrackedEntity = (
    DomainModelBuilder("TrackedEntity")
    .with_entity_fields(timezone_aware=True)
    .with_audit_fields()
    .add_field("data", FieldTemplate(base_type=dict, default_factory=dict))
    .build()
)

# Pattern 3: Soft-deletable entity
SoftEntity = (
    DomainModelBuilder("SoftEntity")
    .with_entity_fields()
    .with_soft_delete()
    .with_audit_fields()
    .add_field("status", FieldTemplate(base_type=str, default="active"))
    .build()
)
```

## Best Practices

### Field Template Design

1. **Reusability**: Design templates for reuse across multiple models
2. **Composition**: Use `as_nullable()` and `as_listable()` for variations
3. **Validation**: Include appropriate validators for data integrity
4. **Documentation**: Provide clear descriptions and examples

### Model Building

1. **Field Families**: Use pre-defined families for consistency
2. **Fluent API**: Leverage DomainModelBuilder for complex models
3. **Protocol Alignment**: Align field choices with protocol requirements
4. **Performance**: Consider validator efficiency and field reuse

---

## Auto-generated API Reference

The following sections contain auto-generated API documentation for all field modules:

## Core Types and Fields

### Field Types

::: pydapter.fields.types
    options:
      show_root_heading: true
      show_source: true

### Field Templates

::: pydapter.fields.template
    options:
      show_root_heading: true
      show_source: true

## Specialized Field Types

### IDs

::: pydapter.fields.ids
    options:
      show_root_heading: true
      show_source: true

### Datetime Fields

::: pydapter.fields.dts
    options:
      show_root_heading: true
      show_source: true

### Embedding Fields

::: pydapter.fields.embedding
    options:
      show_root_heading: true
      show_source: true

### Execution Fields

::: pydapter.fields.execution
    options:
      show_root_heading: true
      show_source: true

### Parameter Fields

::: pydapter.fields.params
    options:
      show_root_heading: true
      show_source: true

## Field Collections

### Common Templates

::: pydapter.fields.common_templates
    options:
      show_root_heading: true
      show_source: true

### Field Families

::: pydapter.fields.families
    options:
      show_root_heading: true
      show_source: true

### Protocol Field Families

::: pydapter.fields.protocol_families
    options:
      show_root_heading: true
      show_source: true

## Builders and Utilities

### Domain Model Builder

::: pydapter.fields.builder
    options:
      show_root_heading: true
      show_source: true

### Validation Patterns

::: pydapter.fields.validation_patterns
    options:
      show_root_heading: true
      show_source: true
