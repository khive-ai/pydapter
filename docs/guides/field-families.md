# Field Families and Common Patterns Library

Field Families provide predefined collections of field templates for rapid
model development. This powerful feature allows you to quickly create models
with standard fields while maintaining consistency across your application.

## 🚀 Quick Start

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate
from pydapter.protocols import (
    create_protocol_model_class,
    IDENTIFIABLE,
    TEMPORAL
)

# Option 1: Build a model with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields()     # id, created_at, updated_at
    .with_soft_delete()       # deleted_at, is_deleted
    .with_audit_fields()      # created_by, updated_by, version
    .add_field("email", FieldTemplate(base_type=str))
    .build()
)

# Option 2: Create a protocol-compliant model with behaviors
User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,  # Adds id field + behavior
    TEMPORAL,      # Adds timestamps + update_timestamp() method
    email=FieldTemplate(base_type=str)
)
```

## 📚 Core Concepts

The Field Families system includes four main components:

1. **FieldFamilies** - Predefined collections of field templates for core
   database patterns
2. **DomainModelBuilder** - Fluent API for building models with method chaining
3. **Protocol Integration** - Type-safe protocol compliance with behavioral
   methods
4. **ValidationPatterns** - Common validation patterns and constraints

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

### 📋 Available Field Families

| Family | Fields | Description |
|--------|--------|-------------|
| **ENTITY** | `id`, `created_at`, `updated_at` | Basic entity fields |
| **ENTITY_TZ** | `id`, `created_at`, `updated_at` | Entity with timezone-aware timestamps |
| **SOFT_DELETE** | `deleted_at`, `is_deleted` | Soft delete support |
| **SOFT_DELETE_TZ** | `deleted_at`, `is_deleted` | Soft delete with timezone-aware timestamp |
| **AUDIT** | `created_by`, `updated_by`, `version` | Audit/tracking fields |

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

## 🔌 Protocol Integration

Create models that comply with pydapter protocols:

### Type-Safe Protocol Constants

```python
from pydapter.protocols import IDENTIFIABLE, TEMPORAL, EMBEDDABLE
from pydapter.fields import create_protocol_model, FieldTemplate

# Use type-safe constants instead of strings
TrackedEntity = create_protocol_model(
    "TrackedEntity",
    IDENTIFIABLE,  # Instead of "identifiable"
    TEMPORAL,      # Instead of "temporal"
)
```

### 🎯 One-Step Protocol Models (Recommended)

Use `create_protocol_model_class` for models with both fields AND behaviors:

```python
from pydapter.protocols import (
    create_protocol_model_class,
    IDENTIFIABLE,
    TEMPORAL
)

# Creates a model with fields AND methods in one step
User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,  # Adds id field + behavior
    TEMPORAL,      # Adds timestamps + update_timestamp() method
    email=FieldTemplate(base_type=str),
    name=FieldTemplate(base_type=str)
)

# Use the model
user = User(email="test@example.com", name="Alice")
user.update_timestamp()  # Method available!
```

### 📋 Supported Protocols

| Protocol | Constant | Fields Added | Methods Added |
|----------|----------|--------------|---------------|
| Identifiable | `IDENTIFIABLE` | `id` | - |
| Temporal | `TEMPORAL` | `created_at`, `updated_at` | `update_timestamp()` |
| Embeddable | `EMBEDDABLE` | `embedding` | `parse_embedding_response()` |
| Invokable | `INVOKABLE` | `execution` | `invoke()` |
| Cryptographical | `CRYPTOGRAPHICAL` | `sha256` | `hash_content()` |

### Alternative Approaches

For more control, you can use these alternative methods:

```python
# Option 1: Structure only (no methods)
from pydapter.fields import create_protocol_model

UserStructure = create_protocol_model(
    "UserStructure",
    IDENTIFIABLE,
    TEMPORAL,
    email=FieldTemplate(base_type=str)
)

# Option 2: Add behaviors to existing model
from pydapter.protocols import combine_with_mixins

User = combine_with_mixins(UserStructure, IDENTIFIABLE, TEMPORAL)

# Option 3: Manual composition
from pydapter.protocols import IdentifiableMixin, TemporalMixin

class User(UserStructure, IdentifiableMixin, TemporalMixin):
    pass
```

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

## 🎯 Best Practices

### 1. **Choose the Right Approach**

| Use Case | Recommended Approach |
|----------|---------------------|
| Simple models with basic fields | `DomainModelBuilder` |
| Protocol-compliant models with behaviors | `create_protocol_model_class()` |
| Structure-only models | `create_protocol_model()` |
| Adding behaviors to existing models | `combine_with_mixins()` |

### 2. **Use Type-Safe Constants**

```python
# ✅ Good - Type-safe and IDE-friendly
from pydapter.protocols import IDENTIFIABLE, TEMPORAL
model = create_protocol_model("Model", IDENTIFIABLE, TEMPORAL)

# ❌ Avoid - String literals are error-prone
model = create_protocol_model("Model", "identifiable", "temporal")
```

### 3. **Start with Core Families**

Begin with the standard field families for consistency:

- `ENTITY` for basic models
- `SOFT_DELETE` for logical deletion
- `AUDIT` for tracking changes

### 4. **Compose for Complex Models**

```python
# Combine multiple patterns
AuditedDocument = (
    DomainModelBuilder("AuditedDocument")
    .with_entity_fields(timezone_aware=True)
    .with_soft_delete()
    .with_audit_fields()
    .add_field("content", FieldTemplate(base_type=str))
    .build()
)
```

### 5. **Preview Before Building**

Always preview your model structure:

```python
builder = DomainModelBuilder("MyModel").with_entity_fields()
print(builder.preview())  # Check fields before building
model = builder.build()
```

### 6. **Keep It Focused**

These families focus on database patterns. For domain-specific logic, create
custom field templates and families.
