# Field Families and Common Patterns Library

Field Families provide predefined collections of field templates for rapid model
development. This feature allows you to quickly create models with standard fields
while maintaining consistency across your application.

## Overview

The Field Families feature includes:

1. **FieldFamilies** - Predefined collections of field templates
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
    FieldFamilies.USER_AUTH,
    FieldFamilies.SOFT_DELETE
)
User = create_model("User", fields=fields)
```

### Available Field Families

- **ENTITY**: Basic entity fields (id, created_at, updated_at)
- **ENTITY_TZ**: Entity fields with timezone-aware timestamps
- **SOFT_DELETE**: Soft delete support (deleted_at, is_deleted)
- **USER_AUTH**: User authentication fields (username, email, password_hash, etc.)
- **USER_PROFILE**: User profile fields (full_name, bio, avatar_url, phone)
- **CONTENT**: Content/article fields (title, content, excerpt, tags, metadata)
- **PRODUCT**: Product fields (name, description, price, currency, sku)
- **ADDRESS**: Address fields (street, city, state, postal_code, country)
- **CONTACT**: Contact information (email, phone, website)
- **SEO**: SEO/metadata fields (meta_title, meta_description, canonical_url)
- **AUDIT**: Audit/tracking fields (created_by, updated_by, version, ip_address)
- **SETTINGS**: Settings/configuration fields (settings, preferences, feature_flags)

## Domain Model Builder

The `DomainModelBuilder` provides a fluent, semantic API for creating models:

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

# Create a blog post model
BlogPost = (
    DomainModelBuilder("BlogPost")
    .with_entity_fields(timezone_aware=True)
    .with_content_fields()
    .with_seo_fields()
    .with_audit_fields()
    .add_field("author_id", ID_TEMPLATE)
    .add_field("status", FieldTemplate(
        base_type=str,
        default="draft",
        description="Publication status"
    ))
    .remove_fields("ip_address")  # Don't need IP tracking
    .build(from_attributes=True)
)
```

### Builder Methods

- `with_entity_fields(timezone_aware=False)` - Add basic entity fields
- `with_soft_delete(timezone_aware=False)` - Add soft delete fields
- `with_user_auth_fields()` - Add user authentication fields
- `with_user_profile_fields()` - Add user profile fields
- `with_content_fields()` - Add content/article fields
- `with_product_fields()` - Add product fields
- `with_address_fields()` - Add address fields
- `with_contact_fields()` - Add contact fields
- `with_seo_fields()` - Add SEO fields
- `with_audit_fields()` - Add audit fields
- `with_settings_fields()` - Add settings fields
- `with_family(family)` - Add a custom field family
- `add_field(name, template, replace=True)` - Add a single field
- `remove_field(name)` - Remove a field
- `remove_fields(*names)` - Remove multiple fields
- `preview()` - Preview fields before building
- `build(**config)` - Build the final model

## Protocol Field Families

Create models that comply with pydapter protocols:

```python
from pydapter.fields import create_protocol_model, FieldTemplate

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
    title=NAME_TEMPLATE,
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
from pydapter.fields import ValidationPatterns, create_pattern_template, create_range_template

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

# Create a user model with all features
User = (
    DomainModelBuilder("User")
    .with_entity_fields(timezone_aware=True)
    .with_user_auth_fields()
    .with_user_profile_fields()
    .with_soft_delete(timezone_aware=True)
    .with_audit_fields()
    # Add custom fields
    .add_field("age", create_range_template(
        int,
        ge=13,
        le=120,
        description="User age"
    ))
    .add_field("website", create_pattern_template(
        ValidationPatterns.HTTPS_URL,
        description="Personal website",
    ).as_nullable())
    .add_field("role", FieldTemplate(
        base_type=str,
        default="user",
        description="User role"
    ))
    # Remove unwanted fields
    .remove_fields("ip_address", "version")
    # Build with configuration
    .build(
        from_attributes=True,
        validate_assignment=True
    )
)

# Create an instance
user = User(
    username="johndoe",
    email="john@example.com",
    password_hash="$2b$12$...",
    full_name="John Doe",
    age=25
)
```

## Best Practices

1. **Start with field families** - Use predefined families as a foundation
2. **Customize as needed** - Add or remove fields to match your requirements
3. **Use validation patterns** - Apply consistent validation across your models
4. **Leverage protocols** - Use protocol families for models that need specific behaviors
5. **Preview before building** - Use `preview()` to verify fields before creating the model
6. **Document custom fields** - Add descriptions to custom fields for clarity
