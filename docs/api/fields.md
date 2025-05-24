# Fields API Reference

The `pydapter.fields` module provides a robust system for defining and managing
data fields with enhanced validation, type transformation, and protocol
integration.

## Installation

```bash
pip install pydapter
```

## Overview

The fields module extends Pydantic's field system with additional features:

- **Enhanced Field Descriptors**: More powerful than standard Pydantic fields
- **Type Transformation**: Convert fields to nullable or listable variants
- **Pre-defined Field Types**: Common field patterns for consistency
- **Validation Integration**: Flexible validator attachment
- **Protocol Support**: Seamless integration with pydapter protocols

## Core Classes

### Field

**Module:** `pydapter.fields.types`

Enhanced field descriptor that provides advanced functionality over Pydantic's
standard fields.

**Constructor:**

```python
class Field:
    def __init__(
        self,
        name: str,
        annotation: type | UndefinedType = Undefined,
        default: Any = Undefined,
        default_factory: Callable | UndefinedType = Undefined,
        title: str | UndefinedType = Undefined,
        description: str | UndefinedType = Undefined,
        examples: list | UndefinedType = Undefined,
        exclude: bool | UndefinedType = Undefined,
        frozen: bool | UndefinedType = Undefined,
        validator: Callable | UndefinedType = Undefined,
        validator_kwargs: dict = Undefined,
        alias: str | UndefinedType = Undefined,
        immutable: bool = False,
        **extra_info: Any,
    )
```

**Key Methods:**

- `copy(**kwargs)`: Create a copy with updated values
- `as_nullable()`: Create nullable variant with None default
- `as_listable(strict=False)`: Create list variant
- `field_info` property: Returns Pydantic FieldInfo object
- `field_validator` property: Returns validator dictionary

**Basic Usage:**

```python
from pydapter.fields import Field

# Define a validated field
name_field = Field(
    name="name",
    annotation=str,
    title="User Name",
    description="The user's full name",
    validator=lambda cls, v: v.strip().title()
)

# Create variants
optional_name = name_field.as_nullable()
name_list = name_field.as_listable()
```

**Advanced Usage:**

```python
# Custom email field with validation
email_field = Field(
    name="email",
    annotation=str,
    validator=lambda cls, v: v.lower() if "@" in v else ValueError("Invalid email"),
    title="Email Address",
    description="User's email address",
    examples=["user@example.com"]
)

# Immutable field
id_field = Field(
    name="id",
    annotation=str,
    immutable=True,
    frozen=True,
    description="Unique identifier"
)
```

### UndefinedType

**Module:** `pydapter.fields.types`

Sentinel type for undefined values in field definitions.

```python
class UndefinedType:
    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> Literal["UNDEFINED"]:
        return "UNDEFINED"

Undefined = UndefinedType()  # Singleton instance
```

**Usage:**

```python
from pydapter.fields.types import Undefined

# Check if value is undefined
if field.default is not Undefined:
    print("Field has a default value")
```

## Pre-defined Fields

### Identifier Fields

**Module:** `pydapter.fields.ids`

#### ID_FROZEN

Immutable UUID field for entity identification.

```python
ID_FROZEN = Field(
    name="id",
    annotation=UUID,
    default_factory=uuid4,
    frozen=True,
    validator=validate_uuid,
    immutable=True
)
```

#### ID_MUTABLE

Mutable UUID field that can be updated.

```python
ID_MUTABLE = Field(
    name="id",
    annotation=UUID,
    default_factory=uuid4,
    validator=validate_uuid
)
```

#### ID_NULLABLE

Optional UUID field that can be None.

```python
ID_NULLABLE = Field(
    name="id",
    annotation=UUID | None,
    default=None,
    validator=validate_uuid
)
```

**Usage:**

```python
from pydapter.fields import ID_FROZEN, create_model

# Use in model creation
User = create_model(
    "User",
    fields=[
        ID_FROZEN.copy(name="user_id"),
        Field(name="name", annotation=str)
    ]
)
```

### DateTime Fields

**Module:** `pydapter.fields.dts`

#### DATETIME

Standard datetime field with UTC timezone.

```python
DATETIME = Field(
    name="timestamp",
    annotation=datetime,
    default_factory=lambda: datetime.now(timezone.utc),
    validator=validate_datetime,
    serializer=datetime_serializer
)
```

#### DATETIME_NULLABLE

Optional datetime field.

```python
DATETIME_NULLABLE = DATETIME.as_nullable()
```

**Validation Function:**

```python
def validate_datetime(cls, v) -> datetime:
    """Validates and ensures timezone-aware datetime"""
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v
```

**Usage:**

```python
from pydapter.fields import DATETIME, DATETIME_NULLABLE

# In model creation
Article = create_model(
    "Article",
    fields=[
        DATETIME.copy(name="created_at"),
        DATETIME_NULLABLE.copy(name="published_at")
    ]
)
```

### Embedding Fields

**Module:** `pydapter.fields.embedding`

#### EMBEDDING

Vector embedding field for AI/ML applications.

```python
EMBEDDING = Field(
    name="embedding",
    annotation=list[float] | None,
    default=None,
    validator=validate_embedding,
    title="Vector Embedding",
    description="High-dimensional vector representation"
)
```

**Validation Function:**

```python
def validate_embedding(cls, v) -> list[float] | None:
    """Validates embedding vectors"""
    if v is None:
        return v
    if not isinstance(v, list):
        raise ValueError("Embedding must be a list")
    if not all(isinstance(x, (int, float)) for x in v):
        raise ValueError("Embedding values must be numeric")
    return [float(x) for x in v]
```

**Usage:**

```python
from pydapter.fields import EMBEDDING

# Document with embedding
Document = create_model(
    "Document",
    fields=[
        Field(name="content", annotation=str),
        EMBEDDING.copy(name="content_embedding")
    ]
)
```

### Execution Fields

**Module:** `pydapter.fields.execution`

#### EXECUTION

Execution state tracking field.

```python
EXECUTION = Field(
    name="execution",
    annotation=Execution,
    default_factory=Execution,
    validator=lambda cls, v: v or Execution(),
    validator_kwargs={"mode": "before"},
    immutable=True
)
```

**Execution Model:**

```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Execution(BaseModel):
    duration: float | None = None           # Execution time in seconds
    response: dict | None = None            # Serialized response
    status: ExecutionStatus = PENDING       # Current status
    error: str | None = None               # Error message if failed
    response_obj: Any = Field(None, exclude=True)  # Original response
    updated_at: datetime | None = Field(    # Last update timestamp
        default_factory=lambda: datetime.now(tz=timezone.utc),
        exclude=True
    )
```

**Usage:**

```python
from pydapter.fields import EXECUTION
from pydapter.fields.execution import ExecutionStatus

# Task with execution tracking
Task = create_model(
    "Task",
    fields=[
        Field(name="name", annotation=str),
        EXECUTION.copy(name="execution")
    ]
)

task = Task(name="Process Data", execution=Execution())
task.execution.status = ExecutionStatus.PROCESSING
```

### Parameter Fields

**Module:** `pydapter.fields.params`

#### PARAMS

General parameter dictionary field.

```python
PARAMS = Field(
    name="params",
    annotation=dict,
    default_factory=dict,
    validator=validate_model_to_params,
    title="Parameters",
    description="Key-value parameter mapping"
)
```

#### PARAM_TYPE

Parameter type field.

```python
PARAM_TYPE = Field(
    name="param_type",
    annotation=type,
    validator=validate_model_to_type,
    title="Parameter Type"
)
```

#### PARAM_TYPE_NULLABLE

Optional parameter type field.

```python
PARAM_TYPE_NULLABLE = PARAM_TYPE.as_nullable()
```

**Validation Functions:**

```python
def validate_model_to_params(v) -> dict:
    """Converts models to parameter dictionaries"""
    if hasattr(v, 'model_dump'):
        return v.model_dump()
    elif isinstance(v, dict):
        return v
    else:
        return {"value": v}

def validate_model_to_type(v) -> type:
    """Validates and extracts type information"""
    if isinstance(v, type):
        return v
    return type(v)
```

## Type Definitions

### Core Types

**Module:** `pydapter.fields.types`

```python
# Basic type aliases
ID = UUID                    # Unique identifier type
Embedding = list[float]      # Vector embedding type
Metadata = dict             # General metadata type
```

**Usage:**

```python
from pydapter.fields.types import ID, Embedding, Metadata

# Type-annotated model
class Document(BaseModel):
    id: ID
    embedding: Embedding
    metadata: Metadata
```

## Utility Functions

### Model Creation

#### create_model

**Function:** `create_model`

Enhanced model creation that integrates with the Field system.

**Signature:**

```python
def create_model(
    model_name: str,
    config: dict[str, Any] = None,
    doc: str = None,
    base: type[BaseModel] = None,
    fields: list[Field] = None,
    frozen: bool = False,
) -> type[BaseModel]
```

**Usage:**

```python
from pydapter.fields import Field, create_model, ID_FROZEN, DATETIME

# Define fields
user_fields = [
    ID_FROZEN.copy(name="id"),
    Field(name="name", annotation=str, title="User Name"),
    Field(name="email", annotation=str, validator=validate_email),
    DATETIME.copy(name="created_at")
]

# Create model
User = create_model(
    model_name="User",
    doc="User model with validation",
    fields=user_fields,
    frozen=True
)

# Use the model
user = User(name="John Doe", email="john@example.com")
```

**Advanced Usage:**

```python
# With base class
class BaseEntity(BaseModel):
    created_by: str

# Custom configuration
config = {"str_strip_whitespace": True}

# Create enhanced model
Product = create_model(
    model_name="Product",
    config=config,
    base=BaseEntity,
    fields=[
        Field(name="name", annotation=str),
        Field(name="price", annotation=float, validator=lambda cls, v: max(0, v))
    ]
)
```

### Validation Functions

#### UUID Validation

**Module:** `pydapter.fields.ids`

```python
def validate_uuid(cls, v) -> UUID:
    """Validates and converts to UUID"""
    if isinstance(v, str):
        return UUID(v)
    elif isinstance(v, UUID):
        return v
    else:
        raise ValueError("Invalid UUID format")

def serialize_uuid(v: UUID) -> str:
    """Serializes UUID to string"""
    return str(v)
```

#### DateTime Validation

**Module:** `pydapter.fields.dts`

```python
def validate_datetime(cls, v) -> datetime:
    """Validates and normalizes datetime"""
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v

def datetime_serializer(v: datetime) -> str:
    """Serializes datetime to ISO format"""
    return v.isoformat()
```

## Advanced Usage

### Custom Field Types

Create reusable field factories:

```python
from pydapter.fields import Field

def create_email_field(name: str, required: bool = True) -> Field:
    """Factory for email fields"""
    def validate_email(cls, v):
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    return Field(
        name=name,
        annotation=str if required else str | None,
        default=None if not required else Undefined,
        validator=validate_email,
        title="Email Address",
        description="A valid email address"
    )

# Usage
user_email = create_email_field("email")
contact_email = create_email_field("contact_email", required=False)
```

### Field Transformation

Use transformation methods for field variants:

```python
# Base field
name_field = Field(name="name", annotation=str)

# Create variants
optional_name = name_field.as_nullable()        # str | None with default=None
name_list = name_field.as_listable(strict=True) # list[str]
flexible_names = name_field.as_listable()       # list[str] | str

# Use in models
UserModel = create_model("User", fields=[
    name_field,
    optional_name.copy(name="nickname"),
    name_list.copy(name="aliases")
])
```

### Protocol Integration

Fields integrate seamlessly with protocols:

```python
from pydapter.fields import ID_FROZEN, DATETIME, EMBEDDING, EXECUTION
from pydapter.protocols.event import BASE_EVENT_FIELDS

# Event uses pre-defined fields
print([f.name for f in BASE_EVENT_FIELDS])
# ['id', 'created_at', 'updated_at', 'embedding', 'execution', 'request', 'content', 'event_type']

# Custom protocol with standard fields
custom_fields = [
    ID_FROZEN.copy(name="id"),
    DATETIME.copy(name="timestamp"),
    Field(name="priority", annotation=int, default=1),
    Field(name="category", annotation=str)
]

CustomEvent = create_model("CustomEvent", fields=custom_fields)
```

### Validation Patterns

Common validation patterns:

```python
# Range validation
def create_range_field(name: str, min_val: int, max_val: int) -> Field:
    def validate_range(cls, v):
        if not min_val <= v <= max_val:
            raise ValueError(f"Value must be between {min_val} and {max_val}")
        return v

    return Field(
        name=name,
        annotation=int,
        validator=validate_range,
        description=f"Integer value between {min_val} and {max_val}"
    )

# String normalization
def create_normalized_string_field(name: str) -> Field:
    def normalize_string(cls, v):
        return v.strip().lower() if v else v

    return Field(
        name=name,
        annotation=str,
        validator=normalize_string
    )

# List validation
def create_validated_list_field(name: str, item_validator: callable) -> Field:
    def validate_list(cls, v):
        if not isinstance(v, list):
            raise ValueError("Value must be a list")
        return [item_validator(cls, item) for item in v]

    return Field(
        name=name,
        annotation=list,
        validator=validate_list
    )
```

## Best Practices

### Field Design

1. **Use Pre-defined Fields**: Leverage existing field definitions for
   consistency
2. **Immutability**: Use `immutable=True` for fields that shouldn't change
3. **Validation**: Always include appropriate validators for data integrity
4. **Documentation**: Provide clear titles and descriptions
5. **Type Safety**: Use proper type annotations

### Model Creation

1. **Field Lists**: Organize fields in logical lists for reuse
2. **Base Classes**: Use base classes for common functionality
3. **Configuration**: Apply consistent model configuration
4. **Frozen Models**: Use `frozen=True` for immutable data structures

### Performance

1. **Validator Efficiency**: Keep validators fast and simple
2. **Field Reuse**: Reuse field definitions instead of recreating
3. **Lazy Evaluation**: Use default factories for expensive computations
4. **Minimal Fields**: Only include fields you actually need

### Integration

1. **Protocol Compatibility**: Design fields to work with protocols
2. **Adapter Support**: Ensure fields work with adapters
3. **Serialization**: Test field serialization/deserialization
4. **Migration**: Plan for field evolution and backward compatibility

## Migration Guide

When upgrading from previous versions:

1. **Field Definitions**: Update to use new Field class
2. **Validation**: Migrate custom validators to new format
3. **Model Creation**: Use `create_model` function
4. **Type Annotations**: Add proper type hints
5. **Protocol Integration**: Leverage pre-defined fields for protocols

For detailed migration instructions, see the
[Migration Guide](../migration_guide.md#fields-system).
