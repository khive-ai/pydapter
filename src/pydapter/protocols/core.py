"""Core protocol implementation with integrated field support."""

from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, Type
from abc import ABCMeta
from functools import lru_cache
import weakref

from ..fields import Schema, SchemaBuilder, FieldTemplate


class ProtocolMeta(ABCMeta):
    """Metaclass for protocols with automatic registration and composition."""

    # Class-level registry of all protocols
    _protocol_registry: weakref.WeakValueDictionary = weakref.WeakValueDictionary()

    def __new__(
        mcs,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs,
    ):
        # Extract protocol configuration
        protocol_id = namespace.pop("__protocol_id__", name.lower())
        required_fields = namespace.pop("__required_fields__", {})
        optional_fields = namespace.pop("__optional_fields__", {})
        behaviors = namespace.pop("__behaviors__", [])

        # Create class
        cls = super().__new__(mcs, name, bases, namespace)

        # Set protocol attributes
        cls.__protocol_id__ = protocol_id
        cls.__required_fields__ = required_fields
        cls.__optional_fields__ = optional_fields
        cls.__behaviors__ = behaviors

        # Register protocol
        mcs._protocol_registry[protocol_id] = cls

        return cls

    @classmethod
    def get_protocol(mcs, protocol_id: str) -> Optional[Type["Protocol"]]:
        """Get protocol by ID."""
        return mcs._protocol_registry.get(protocol_id)

    @classmethod
    def all_protocols(mcs) -> Dict[str, Type["Protocol"]]:
        """Get all registered protocols."""
        return dict(mcs._protocol_registry)


class Protocol(metaclass=ProtocolMeta):
    """
    Base protocol class for defining reusable behaviors.
    
    Protocols define:
    - Required and optional fields
    - Behaviors (methods that operate on those fields)
    - Composition rules with other protocols
    """

    __protocol_id__: ClassVar[str]
    __required_fields__: ClassVar[Dict[str, FieldTemplate]]
    __optional_fields__: ClassVar[Dict[str, FieldTemplate]]
    __behaviors__: ClassVar[List[str]]

    def __init_subclass__(cls, protocol_id: Optional[str] = None, **kwargs):
        """Initialize subclass with protocol configuration."""
        super().__init_subclass__(**kwargs)

        if protocol_id:
            cls.__protocol_id__ = protocol_id

    @classmethod
    @lru_cache(maxsize=128)
    def get_schema(cls) -> Schema:
        """Get schema for this protocol."""
        builder = SchemaBuilder(f"{cls.__name__}Schema")

        # Add required fields
        for name, template in cls.__required_fields__.items():
            builder.add_field(name, template, {"required": True, "protocol": cls.__protocol_id__})

        # Add optional fields
        for name, template in cls.__optional_fields__.items():
            builder.add_field(name, template, {"required": False, "protocol": cls.__protocol_id__})

        return builder.build()

    @classmethod
    def get_all_fields(cls) -> Dict[str, FieldTemplate]:
        """Get all fields (required + optional)."""
        return {**cls.__required_fields__, **cls.__optional_fields__}

    @classmethod
    def validate_implementation(cls, obj: Any) -> bool:
        """Check if an object implements this protocol."""
        # Check required fields
        for field_name in cls.__required_fields__:
            if not hasattr(obj, field_name):
                return False

        # Check behaviors
        for behavior in cls.__behaviors__:
            if not hasattr(obj, behavior) or not callable(getattr(obj, behavior)):
                return False

        return True

    @classmethod
    def apply_to_schema(cls, schema: Schema) -> Schema:
        """Apply this protocol to an existing schema."""
        # Merge fields
        protocol_schema = cls.get_schema()
        return schema.merge(protocol_schema)

    @classmethod
    def create_mixin(cls) -> Type:
        """Create a mixin class with protocol behaviors."""
        # Create namespace with behavior methods
        namespace = {"__protocol_id__": cls.__protocol_id__}
        
        # Add behavior methods
        for behavior in cls.__behaviors__:
            if hasattr(cls, behavior):
                namespace[behavior] = getattr(cls, behavior)
        
        # Create mixin class
        mixin_name = f"{cls.__name__}Mixin"
        return type(mixin_name, (), namespace)

    def __repr__(self) -> str:
        """String representation."""
        return f"<Protocol {self.__protocol_id__}>"


class ProtocolRegistry:
    """
    Thread-safe registry for protocol management.
    Handles registration, lookup, and composition.
    """

    def __init__(self):
        self._protocols: Dict[str, Type[Protocol]] = {}
        self._compositions: Dict[frozenset[str], Type[Protocol]] = {}

    def register(self, protocol: Type[Protocol]) -> None:
        """Register a protocol."""
        self._protocols[protocol.__protocol_id__] = protocol

    def get(self, protocol_id: str) -> Optional[Type[Protocol]]:
        """Get protocol by ID."""
        return self._protocols.get(protocol_id)

    def get_all(self) -> Dict[str, Type[Protocol]]:
        """Get all registered protocols."""
        return self._protocols.copy()

    @lru_cache(maxsize=256)
    def find_protocols_with_field(self, field_name: str) -> List[Type[Protocol]]:
        """Find all protocols that have a specific field."""
        result = []
        for protocol in self._protocols.values():
            if field_name in protocol.get_all_fields():
                result.append(protocol)
        return result

    def register_composition(
        self, protocol_ids: Set[str], composed_protocol: Type[Protocol]
    ) -> None:
        """Register a composed protocol."""
        key = frozenset(protocol_ids)
        self._compositions[key] = composed_protocol

    def get_composition(self, protocol_ids: Set[str]) -> Optional[Type[Protocol]]:
        """Get composed protocol."""
        key = frozenset(protocol_ids)
        return self._compositions.get(key)

    def clear(self) -> None:
        """Clear all registrations."""
        self._protocols.clear()
        self._compositions.clear()


# Global registry instance
protocol_registry = ProtocolRegistry()