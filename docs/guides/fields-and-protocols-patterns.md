# Fields and Protocols: Best Usage Patterns

This guide demonstrates the best practices for using pydapter's field system with
protocols to create consistent, type-safe models for database operations.

## Core Concepts

### 1. Field Templates vs Direct Fields

- **Field Templates**: Reusable definitions that can create fields with different names
- **Protocol Families**: Pre-defined field sets that match protocol requirements
- **Field Families**: Logical groupings for common database patterns

### 2. Protocol Alignment

Protocols define behavioral contracts. Use protocol-specific field families to ensure
your models can leverage protocol functionality.

## Pattern 1: Basic Entity with Protocols

For most database entities, combine Identifiable and Temporal protocols:

```python
from pydapter.fields import create_protocol_model, FieldTemplate

# Simple entity
User = create_protocol_model(
    "User",
    "identifiable",
    "temporal",
    # Add domain-specific fields
    username=FieldTemplate(base_type=str, max_length=50),
    email=FieldTemplate(base_type=str),
    is_active=FieldTemplate(base_type=bool, default=True)
)

# The model now has: id, created_at, updated_at, username, email, is_active
# And can be used with any adapter that expects Identifiable/Temporal protocols
```

## Pattern 2: Versioned Entities with Audit Trail

For entities requiring version control and audit tracking:

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

Order = (
    DomainModelBuilder("Order")
    .with_entity_fields(timezone_aware=True)  # id, created_at, updated_at
    .with_audit_fields()                      # created_by, updated_by, version
    .add_field("order_number", FieldTemplate(
        base_type=str,
        description="Unique order identifier"
    ))
    .add_field("total_amount", FieldTemplate(
        base_type=float,
        ge=0,
        description="Order total"
    ))
    .add_field("status", FieldTemplate(
        base_type=str,
        default="pending",
        description="Order status"
    ))
    .build()
)
```

## Pattern 3: Soft-Deletable Entities

For entities that should never be hard-deleted:

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate

Product = (
    DomainModelBuilder("Product")
    .with_entity_fields()
    .with_soft_delete()  # Adds deleted_at, is_deleted
    .add_field("name", FieldTemplate(base_type=str))
    .add_field("sku", FieldTemplate(base_type=str))
    .add_field("price", FieldTemplate(base_type=float, ge=0))
    .build()
)

# Usage in queries
async def get_active_products(adapter):
    return await adapter.find_many({"is_deleted": False})
```

## Pattern 4: Embeddable Documents

For vector search and similarity operations:

```python
from pydapter.fields import create_protocol_model, FieldTemplate

Document = create_protocol_model(
    "Document",
    "identifiable",
    "temporal",
    "embeddable",  # Adds embedding field
    title=FieldTemplate(base_type=str),
    content=FieldTemplate(base_type=str),
    metadata=FieldTemplate(
        base_type=dict,
        default_factory=dict,
        description="Additional document metadata"
    )
)

# Usage with vector adapters
async def search_similar(adapter, query_embedding):
    return await adapter.similarity_search(
        embedding=query_embedding,
        limit=10
    )
```

## Pattern 5: Event Sourcing

For event-driven architectures using the complete Event protocol:

```python
from pydapter.fields import create_protocol_model, FieldTemplate
from pydapter.fields.execution import Execution

# EVENT_COMPLETE includes all event-related fields
UserEvent = create_protocol_model(
    "UserEvent",
    "event",  # Includes: id, created_at, updated_at, event_type, content,
              # request, embedding, sha256, execution
    user_id=FieldTemplate(base_type=str),
    action=FieldTemplate(base_type=str),
    details=FieldTemplate(
        base_type=dict,
        default_factory=dict
    )
)

# Create events
login_event = UserEvent(
    event_type="user.login",
    user_id="user123",
    action="login",
    content={"ip": "192.168.1.1", "user_agent": "..."},
    request={"endpoint": "/api/login", "method": "POST"}
)
```

## Pattern 6: Custom Protocol Combinations

Mix protocols based on your needs:

```python
# Cryptographically signed document
SignedDocument = create_protocol_model(
    "SignedDocument",
    "identifiable",
    "temporal",
    "cryptographical",  # Adds sha256 field
    document_type=FieldTemplate(base_type=str),
    content=FieldTemplate(base_type=str),
    signature=FieldTemplate(base_type=str)
)

# Executable task with tracking
Task = create_protocol_model(
    "Task",
    "identifiable",
    "temporal",
    "invokable",  # Adds execution field
    name=FieldTemplate(base_type=str),
    parameters=FieldTemplate(base_type=dict, default_factory=dict),
    status=FieldTemplate(base_type=str, default="pending")
)
```

## Pattern 7: Validation Patterns

Use pre-built validation patterns for common field types:

```python
from pydapter.fields import (
    create_pattern_template,
    create_range_template,
    ValidationPatterns,
    DomainModelBuilder
)

UserProfile = (
    DomainModelBuilder("UserProfile")
    .with_entity_fields()
    .add_field("username", create_pattern_template(
        ValidationPatterns.USERNAME_ALPHANUMERIC,
        description="Alphanumeric username"
    ))
    .add_field("email", create_pattern_template(
        ValidationPatterns.EMAIL,
        description="User email address"
    ))
    .add_field("age", create_range_template(
        int,
        ge=13,
        le=120,
        description="User age"
    ))
    .add_field("website", create_pattern_template(
        ValidationPatterns.HTTPS_URL,
        description="Personal website",
        default=None
    ).as_nullable())
    .build()
)
```

## Pattern 8: Adapter-Specific Metadata

Add metadata for adapter optimization:

```python
from pydapter.fields import FieldTemplate, DomainModelBuilder

SearchableProduct = (
    DomainModelBuilder("SearchableProduct")
    .with_entity_fields()
    .add_field("name", FieldTemplate(
        base_type=str,
        json_schema_extra={"db_index": True}
    ))
    .add_field("description", FieldTemplate(
        base_type=str,
        json_schema_extra={"db_fulltext": True}
    ))
    .add_field("tags", FieldTemplate(
        base_type=list[str],
        default_factory=list,
        json_schema_extra={"db_index": True}
    ))
    .add_field("embedding", FieldTemplate(
        base_type=list[float],
        default_factory=list,
        json_schema_extra={
            "vector_dim": 1536,
            "index_type": "hnsw",
            "distance_metric": "cosine"
        }
    ))
    .build()
)
```

## Best Practices

### 1. Choose the Right Pattern

- **Simple CRUD**: Use `create_protocol_model` with "identifiable" and "temporal"
- **Audit Requirements**: Add audit fields with `.with_audit_fields()`
- **Soft Delete**: Use `.with_soft_delete()` for logical deletion
- **Event Sourcing**: Use the "event" protocol for complete event tracking

### 2. Protocol Selection Guidelines

```python
# Minimal entity
Model = create_protocol_model("Model", "identifiable")

# Standard entity with timestamps
Model = create_protocol_model("Model", "identifiable", "temporal")

# Searchable content
Model = create_protocol_model("Model", "identifiable", "temporal", "embeddable")

# Event with all tracking
Model = create_protocol_model("Model", "event")
```

### 3. Field Template Reuse

```python
# Define common templates once
from pydapter.fields import FieldTemplate

# Reusable templates
MONEY = FieldTemplate(
    base_type=float,
    ge=0,
    description="Monetary amount",
    json_schema_extra={"format": "money", "decimal_places": 2}
)

STATUS = FieldTemplate(
    base_type=str,
    description="Status field",
    default="active",
    json_schema_extra={"enum": ["active", "inactive", "pending"]}
)

# Use across models
Invoice = create_protocol_model(
    "Invoice",
    "identifiable",
    "temporal",
    amount=MONEY,
    status=STATUS
)

Payment = create_protocol_model(
    "Payment",
    "identifiable",
    "temporal",
    amount=MONEY,
    status=STATUS.copy(default="pending")
)
```

### 4. Timezone Awareness

Always specify timezone awareness explicitly:

```python
# Timezone-aware (recommended for distributed systems)
Model = create_protocol_model("Model", "temporal", timezone_aware=True)

# Naive datetime (only for single-timezone applications)
Model = create_protocol_model("Model", "temporal", timezone_aware=False)
```

### 5. Composing Complex Models

For complex requirements, combine approaches:

```python
# Start with protocol model, then enhance
BaseOrder = create_protocol_model(
    "BaseOrder",
    "identifiable",
    "temporal",
    order_number=FieldTemplate(base_type=str)
)

# Extend with builder pattern
CompleteOrder = (
    DomainModelBuilder("CompleteOrder")
    .with_family({
        "id": BaseOrder.model_fields["id"],
        "created_at": BaseOrder.model_fields["created_at"],
        "updated_at": BaseOrder.model_fields["updated_at"],
        "order_number": BaseOrder.model_fields["order_number"]
    })
    .with_soft_delete()
    .with_audit_fields()
    .add_field("items", FieldTemplate(
        base_type=list[dict],
        default_factory=list
    ))
    .build()
)
```

## Migration Strategy

When migrating existing models:

1. Identify which protocols your model should implement
2. Use `create_protocol_model` to ensure protocol compliance
3. Add domain-specific fields as extra parameters
4. Gradually refactor to use field families for consistency

```python
# Before
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    username: str
    email: str

# After
User = create_protocol_model(
    "User",
    "identifiable",
    "temporal",
    username=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str)
)
```

This approach ensures protocol compliance while maintaining flexibility for
domain-specific needs.
