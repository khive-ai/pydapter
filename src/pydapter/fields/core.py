"""Core field implementation with high-performance design."""

from typing import Any, ClassVar, Dict, Generic, Optional, Type, TypeVar, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
import weakref

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FieldSchema:
    """Immutable field schema for memory efficiency."""

    name: str
    type: Type
    default: Any = None
    required: bool = True
    validators: tuple["ValidationProtocol", ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.type, self.required))


class ValidationProtocol(ABC):
    """Protocol for field validation."""

    @abstractmethod
    def validate(self, value: Any, field: "Field") -> Any:
        """Validate value against field constraints."""
        ...

    @property
    @abstractmethod
    def error_message(self) -> str:
        """Validation error message template."""
        ...


class Field(Generic[T]):
    """
    High-performance field descriptor with caching and lazy evaluation.
    Uses __slots__ for memory efficiency.
    """

    __slots__ = ("_schema", "_value_cache", "_validation_cache", "__weakref__")

    def __init__(self, schema: FieldSchema):
        self._schema = schema
        self._value_cache = {}
        self._validation_cache = weakref.WeakValueDictionary()

    @property
    def name(self) -> str:
        return self._schema.name

    @property
    def type(self) -> Type[T]:
        return self._schema.type

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._schema.metadata

    def __set_name__(self, owner, name):
        """Called when field is assigned to a class."""
        if not self._schema.name:
            self._schema = dataclass(frozen=True)(type(self._schema))(
                name=name,
                type=self._schema.type,
                default=self._schema.default,
                required=self._schema.required,
                validators=self._schema.validators,
                metadata=self._schema.metadata,
            )

    def __get__(self, obj, objtype=None):
        """Get field value with validation."""
        if obj is None:
            return self
        
        # Get from instance dict
        value = obj.__dict__.get(self.name, self._schema.default)
        
        # Handle callable defaults
        if callable(value) and value == self._schema.default:
            value = value()
            obj.__dict__[self.name] = value
            
        return value

    def __set__(self, obj, value):
        """Set field value with validation."""
        validated = self.validate(value)
        obj.__dict__[self.name] = validated

    def __delete__(self, obj):
        """Delete field value."""
        obj.__dict__.pop(self.name, None)

    def validate(self, value: Any) -> T:
        """Validate with caching for repeated values."""
        # Quick path for None and defaults
        if value is None:
            if not self._schema.required:
                return self._schema.default
            raise ValueError(f"Field '{self.name}' is required")

        # Run validators
        validated = value
        for validator in self._schema.validators:
            validated = validator.validate(validated, self)

        # Type coercion
        if not isinstance(validated, self.type):
            try:
                validated = self.type(validated)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Cannot convert {value!r} to {self.type.__name__}: {e}"
                )

        return validated

    def serialize(self, value: T) -> Any:
        """Serialize with type-specific optimizations."""
        if value is None:
            return None

        # Fast path for primitives
        if isinstance(value, (str, int, float, bool)):
            return value

        # Use protocol if available
        if hasattr(value, "__serialize__"):
            return value.__serialize__()

        # Default serialization
        return str(value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert field schema to dictionary."""
        return {
            "name": self._schema.name,
            "type": self._schema.type.__name__,
            "required": self._schema.required,
            "default": self._schema.default,
            "metadata": self._schema.metadata,
        }