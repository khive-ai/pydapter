# Field Families and Common Patterns Library

Field Families provide predefined collections of field templates for rapid model
development. This feature allows you to quickly create models with standard fields
while maintaining consistency across your application.

## Overview

The Field Families feature includes:

1. **FieldFamilies** - Predefined collections of field templates for core database patterns
2. **DomainModelBuilder** - Fluent API for building models
3. **ProtocolFieldFamilies** - Field families for protocol compliance
4. **ValidationPatterns** - Common validation patterns for fields

## Using Field Families

### Basic Usage

```python
from pydapter.fields import FieldFamilies, create_field_dict, create_model

# Create a model with entity fields
fields = create_field_dict(FieldFamilies.ENTITY)
EntityModel = create_model("EntityModel", fields=fields)

# Combine multiple families
fields = create_field_dict(
    FieldFamilies.ENTITY,
    FieldFamilies.AUDIT,
    FieldFamilies.SOFT_DELETE
)
TrackedModel = create_model("TrackedModel", fields=fields)
```

### Available Field Families

- **ENTITY**: Basic entity fields (id, created_at, updated_at)
- **ENTITY_TZ**: Entity fields with timezone-aware timestamps
- **SOFT_DELETE**: Soft delete support (deleted_at, is_deleted)
- **SOFT_DELETE_TZ**: Soft delete with timezone-aware timestamp
- **AUDIT**: Audit/tracking fields (created_by, updated_by, version)

## Domain Model Builder

The `DomainModelBuilder` provides a fluent API for creating models:

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

# Create a tracked entity model
TrackedEntity = (
    DomainModelBuilder("TrackedEntity")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete(timezone_aware=True)
    .with_audit_fields()
    .add_field("name", FieldTemplate(
        base_type=str,
        description="Entity name"
    ))
    .add_field("status", FieldTemplate(
        base_type=str,
        default="active",
        description="Entity status"
    ))
    .build(from_attributes=True)
)
```

### Builder Methods

- `with_entity_fields(timezone_aware=False)` - Add basic entity fields
- `with_soft_delete(timezone_aware=False)` - Add soft delete fields
- `with_audit_fields()` - Add audit fields
- `with_family(family)` - Add a custom field family
- `add_field(name, template, replace=True)` - Add a single field
- `remove_field(name)` - Remove a field
- `remove_fields(*names)` - Remove multiple fields
- `preview()` - Preview fields before building
- `build(**config)` - Build the final model

## Protocol Field Families

Create models that comply with pydapter protocols:

```python
from pydapter.fields import create_protocol_model, FieldTemplate, ID_TEMPLATE

# Create a model with ID and timestamps
TrackedEntity = create_protocol_model(
    "TrackedEntity",
    "identifiable",
    "temporal",
)

# Create an event model with custom fields
CustomEvent = create_protocol_model(
    "CustomEvent",
    "event",
    user_id=ID_TEMPLATE,
    action=FieldTemplate(base_type=str, description="User action"),
)

# Create an embeddable document
Document = create_protocol_model(
    "Document",
    "identifiable",
    "temporal",
    "embeddable",
    title=FieldTemplate(base_type=str, description="Document title"),
    content=FieldTemplate(base_type=str),
)
```

### Supported Protocols

- `"identifiable"` - Adds id field
- `"temporal"` - Adds created_at and updated_at fields
- `"embeddable"` - Adds embedding field
- `"invokable"` - Adds execution field
- `"cryptographical"` - Adds sha256 field
- `"event"` - Adds all Event protocol fields

## Validation Patterns

Use pre-built validation patterns for common field types:

```python
from pydapter.fields import (
    ValidationPatterns,
    create_pattern_template,
    create_range_template
)

# Use pre-built patterns
email_field = create_pattern_template(
    ValidationPatterns.EMAIL,
    description="User email address",
    error_message="Please enter a valid email"
)

# Create custom patterns
product_code = create_pattern_template(
    r"^[A-Z]{2}\d{4}$",
    description="Product code",
    error_message="Product code must be 2 letters followed by 4 digits"
)

# Create range-constrained fields
age = create_range_template(
    int,
    ge=0,
    le=150,
    description="Person's age"
)

percentage = create_range_template(
    float,
    ge=0,
    le=100,
    description="Percentage value",
    default=0.0
)
```

### Available Patterns

ValidationPatterns provides regex patterns for:

- Email addresses
- URLs (HTTP/HTTPS)
- Phone numbers (US and international)
- Usernames
- Passwords
- Slugs and identifiers
- Color codes
- Dates and times
- Geographic data (latitude, longitude, ZIP codes)
- Financial data (credit cards, IBAN, Bitcoin addresses)
- Social media handles

## Complete Example

Here's a complete example combining all features:

```python
from pydapter.fields import (
    DomainModelBuilder,
    FieldTemplate,
    ValidationPatterns,
    create_pattern_template,
    create_range_template,
)

# Create an audited entity with validation
AuditedEntity = (
    DomainModelBuilder("AuditedEntity")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete(timezone_aware=True)
    .with_audit_fields()
    # Add custom fields with validation
    .add_field("name", FieldTemplate(
        base_type=str,
        min_length=1,
        max_length=100,
        description="Entity name"
    ))
    .add_field("email", create_pattern_template(
        ValidationPatterns.EMAIL,
        description="Contact email"
    ))
    .add_field("age", create_range_template(
        int,
        ge=0,
        le=150,
        description="Age in years"
    ))
    .add_field("score", create_range_template(
        float,
        ge=0,
        le=100,
        description="Score percentage"
    ))
    .add_field("website", create_pattern_template(
        ValidationPatterns.HTTPS_URL,
        description="Website URL",
    ).as_nullable())
    # Build with configuration
    .build(
        from_attributes=True,
        validate_assignment=True
    )
)

# Create an instance
entity = AuditedEntity(
    name="Example Entity",
    email="contact@example.com",
    age=25,
    score=85.5
)
```

## Best Practices

1. **Use core families** - Start with ENTITY, SOFT_DELETE, and AUDIT families
2. **Leverage protocols** - Use protocol families for models that need specific behaviors
3. **Apply validation** - Use validation patterns for consistent data validation
4. **Compose families** - Combine multiple families to build comprehensive models
5. **Preview before building** - Use `preview()` to verify fields before creating the model
6. **Keep it focused** - These families focus on database patterns, not domain-specific logic
