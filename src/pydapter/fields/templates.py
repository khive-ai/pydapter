"""Field templates with compositional design."""

from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar, Union
from datetime import datetime, timezone
from decimal import Decimal
import re
import uuid

from .core import Field, FieldSchema, ValidationProtocol

T = TypeVar("T")


class FieldTemplate(Generic[T]):
    """
    Base template for field definitions using compositional pattern.
    Templates are immutable and reusable across multiple models.
    """

    def __init__(
        self,
        type_: Type[T],
        *,
        default: Optional[Union[T, Callable[[], T]]] = None,
        required: bool = True,
        validators: Optional[list[ValidationProtocol]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.type = type_
        self.default = default
        self.required = required
        self.validators = tuple(validators or [])
        self.metadata = metadata or {}

    def create_field(self, name: str = "") -> Field[T]:
        """Create a field instance from this template."""
        schema = FieldSchema(
            name=name,
            type=self.type,
            default=self.default,
            required=self.required,
            validators=self.validators,
            metadata=self.metadata,
        )
        return Field(schema)

    def __call__(self, **overrides) -> Field[T]:
        """Create field with overrides."""
        name = overrides.pop("name", "")
        
        # Merge configurations
        kwargs = {
            "type_": self.type,
            "default": overrides.get("default", self.default),
            "required": overrides.get("required", self.required),
            "validators": list(self.validators) + overrides.get("validators", []),
            "metadata": {**self.metadata, **overrides.get("metadata", {})},
        }
        
        # Create new template and field
        template = FieldTemplate(**kwargs)
        return template.create_field(name)

    def as_optional(self, default: Optional[T] = None) -> "FieldTemplate[Optional[T]]":
        """Create optional version of this field."""
        return FieldTemplate(
            Optional[self.type],
            default=default,
            required=False,
            validators=list(self.validators),
            metadata=self.metadata,
        )

    def with_validators(self, *validators: ValidationProtocol) -> "FieldTemplate[T]":
        """Add validators to this template."""
        return FieldTemplate(
            self.type,
            default=self.default,
            required=self.required,
            validators=list(self.validators) + list(validators),
            metadata=self.metadata,
        )

    def with_metadata(self, **metadata) -> "FieldTemplate[T]":
        """Add metadata to this template."""
        return FieldTemplate(
            self.type,
            default=self.default,
            required=self.required,
            validators=list(self.validators),
            metadata={**self.metadata, **metadata},
        )


# Validation implementations
class StringValidator(ValidationProtocol):
    """String validation with constraints."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Any, field: Field) -> str:
        if not isinstance(value, str):
            value = str(value)

        if self.min_length and len(value) < self.min_length:
            raise ValueError(f"String too short (min: {self.min_length})")

        if self.max_length and len(value) > self.max_length:
            raise ValueError(f"String too long (max: {self.max_length})")

        if self.pattern and not self.pattern.match(value):
            raise ValueError("String does not match pattern")

        return value

    @property
    def error_message(self) -> str:
        return "String validation failed"


class NumericValidator(ValidationProtocol):
    """Numeric validation with bounds."""

    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        type_: Type = int,
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.type = type_

    def validate(self, value: Any, field: Field) -> Any:
        try:
            value = self.type(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert to {self.type.__name__}")

        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Value below minimum ({self.min_value})")

        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Value above maximum ({self.max_value})")

        return value

    @property
    def error_message(self) -> str:
        return "Numeric validation failed"


class DateTimeValidator(ValidationProtocol):
    """DateTime validation with timezone handling."""

    def __init__(self, timezone_aware: bool = True):
        self.timezone_aware = timezone_aware

    def validate(self, value: Any, field: Field) -> datetime:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            # Simple ISO format parsing
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise ValueError(f"Cannot parse datetime from {type(value)}")

        if self.timezone_aware and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif not self.timezone_aware and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        return dt

    @property
    def error_message(self) -> str:
        return "DateTime validation failed"


# Common field templates
def StringField(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    **kwargs,
) -> FieldTemplate[str]:
    """String field with validation."""
    validators = kwargs.pop("validators", [])
    validators.append(StringValidator(min_length, max_length, pattern))
    return FieldTemplate(str, validators=validators, **kwargs)


def IntField(
    min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs
) -> FieldTemplate[int]:
    """Integer field with bounds checking."""
    validators = kwargs.pop("validators", [])
    validators.append(NumericValidator(min_value, max_value, int))
    return FieldTemplate(int, validators=validators, **kwargs)


def FloatField(
    min_value: Optional[float] = None, max_value: Optional[float] = None, **kwargs
) -> FieldTemplate[float]:
    """Float field with bounds checking."""
    validators = kwargs.pop("validators", [])
    validators.append(NumericValidator(min_value, max_value, float))
    return FieldTemplate(float, validators=validators, **kwargs)


def BoolField(**kwargs) -> FieldTemplate[bool]:
    """Boolean field."""
    return FieldTemplate(bool, **kwargs)


def DateTimeField(
    timezone_aware: bool = True,
    auto_now: bool = False,
    auto_now_add: bool = False,
    **kwargs,
) -> FieldTemplate[datetime]:
    """DateTime field with timezone support."""
    validators = kwargs.pop("validators", [])
    validators.append(DateTimeValidator(timezone_aware))

    metadata = kwargs.get("metadata", {})
    metadata.update(
        {
            "temporal": True,
            "auto_now": auto_now,
            "auto_now_add": auto_now_add,
            "timezone_aware": timezone_aware,
        }
    )
    kwargs["metadata"] = metadata

    # Handle auto defaults
    if auto_now_add and "default" not in kwargs:
        kwargs["default"] = lambda: datetime.now(
            timezone.utc if timezone_aware else None
        )

    return FieldTemplate(datetime, validators=validators, **kwargs)


def UUIDField(auto_generate: bool = True, **kwargs) -> FieldTemplate[uuid.UUID]:
    """UUID field with auto-generation support."""
    if auto_generate and "default" not in kwargs:
        kwargs["default"] = uuid.uuid4

    metadata = kwargs.get("metadata", {})
    metadata.update({"identifier": True, "auto_generate": auto_generate})
    kwargs["metadata"] = metadata

    return FieldTemplate(uuid.UUID, **kwargs)


def DecimalField(
    max_digits: Optional[int] = None, decimal_places: Optional[int] = None, **kwargs
) -> FieldTemplate[Decimal]:
    """Decimal field for precise numeric values."""
    metadata = kwargs.get("metadata", {})
    metadata.update({"max_digits": max_digits, "decimal_places": decimal_places})
    kwargs["metadata"] = metadata

    return FieldTemplate(Decimal, **kwargs)


def ListField(item_type: Optional[Type] = None, **kwargs) -> FieldTemplate[list]:
    """List field with optional item type validation."""
    metadata = kwargs.get("metadata", {})
    metadata.update({"item_type": item_type})
    kwargs["metadata"] = metadata

    if "default" not in kwargs:
        kwargs["default"] = list

    return FieldTemplate(list, **kwargs)


def DictField(
    key_type: Optional[Type] = None, value_type: Optional[Type] = None, **kwargs
) -> FieldTemplate[dict]:
    """Dictionary field with optional type validation."""
    metadata = kwargs.get("metadata", {})
    metadata.update({"key_type": key_type, "value_type": value_type})
    kwargs["metadata"] = metadata

    if "default" not in kwargs:
        kwargs["default"] = dict

    return FieldTemplate(dict, **kwargs)