"""Factory functions for creating protocol-based models."""

from typing import Any, Dict, List, Optional, Type, Union
from functools import lru_cache

from .core import Protocol, ProtocolMeta
from .composition import compose_protocols
from ..fields import Schema, SchemaBuilder, Field


class ProtocolModel:
    """Base class for protocol-based models with automatic field and behavior integration."""
    
    __protocols__: List[Type[Protocol]] = []
    __schema__: Schema = None
    
    def __init__(self, **kwargs):
        """Initialize model with field values."""
        # Get all fields from schema
        if self.__schema__:
            fields = self.__schema__.create_fields()
            
            # Validate required fields
            required = set(self.__schema__.required_fields)
            provided = set(kwargs.keys())
            missing = required - provided
            
            if missing:
                raise TypeError(f"Missing required fields: {missing}")
            
            # Set field values
            for name, field in fields.items():
                if name in kwargs:
                    setattr(self, name, kwargs[name])
                elif not field._schema.required:
                    # Set default for optional fields
                    default = field._schema.default
                    if callable(default):
                        setattr(self, name, default())
                    else:
                        setattr(self, name, default)
    
    @classmethod
    def get_protocols(cls) -> List[Type[Protocol]]:
        """Get all protocols implemented by this model."""
        return cls.__protocols__
    
    @classmethod
    def implements_protocol(cls, protocol: Union[str, Type[Protocol]]) -> bool:
        """Check if model implements a specific protocol."""
        if isinstance(protocol, str):
            protocol = ProtocolMeta.get_protocol(protocol)
        
        return protocol in cls.__protocols__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        if self.__schema__:
            for field_name in self.__schema__.field_names:
                if hasattr(self, field_name):
                    value = getattr(self, field_name)
                    # Handle serialization
                    field = self.__schema__.fields[field_name].template.create_field(field_name)
                    result[field_name] = field.serialize(value)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolModel":
        """Create model from dictionary."""
        return cls(**data)
    
    def __repr__(self) -> str:
        """String representation."""
        fields = []
        if self.__schema__:
            for name in self.__schema__.field_names:
                if hasattr(self, name):
                    value = getattr(self, name)
                    fields.append(f"{name}={value!r}")
        
        return f"{self.__class__.__name__}({', '.join(fields)})"


@lru_cache(maxsize=256)
def create_protocol_model(
    name: str,
    *protocol_ids: str,
    additional_fields: Optional[Dict[str, Any]] = None,
    base_class: Type[ProtocolModel] = ProtocolModel,
) -> Type[ProtocolModel]:
    """
    Create a model class that implements multiple protocols.
    
    Args:
        name: Name for the model class
        protocol_ids: IDs of protocols to implement
        additional_fields: Additional fields beyond protocol requirements
        base_class: Base class to extend from
    
    Returns:
        Model class with integrated fields and behaviors
    
    Example:
        User = create_protocol_model(
            "User",
            "identifiable",
            "temporal",
            "auditable",
            additional_fields={
                "email": StringField(required=True),
                "name": StringField(required=True),
            }
        )
    """
    # Get protocols
    protocols = []
    for protocol_id in protocol_ids:
        protocol = ProtocolMeta.get_protocol(protocol_id)
        if not protocol:
            raise ValueError(f"Unknown protocol: {protocol_id}")
        protocols.append(protocol)
    
    # Build schema from protocols
    builder = SchemaBuilder(name)
    
    # Add protocol fields
    for protocol in protocols:
        schema = protocol.get_schema()
        for field_name, schema_field in schema.fields.items():
            # Check for conflicts
            if field_name not in builder.fields:
                builder.add_field(
                    field_name,
                    schema_field.template,
                    schema_field.metadata
                )
    
    # Add additional fields
    if additional_fields:
        for field_name, field_template in additional_fields.items():
            builder.add_field(field_name, field_template)
    
    # Build final schema
    schema = builder.build()
    
    # Create namespace
    namespace = {
        "__protocols__": protocols,
        "__schema__": schema,
        "__module__": "pydapter.protocols.models",
    }
    
    # Add behavior methods from all protocols
    for protocol in protocols:
        for behavior in protocol.__behaviors__:
            if hasattr(protocol, behavior):
                method = getattr(protocol, behavior)
                namespace[behavior] = method
    
    # Add field descriptors
    fields = schema.create_fields()
    for field_name, field in fields.items():
        namespace[field_name] = field
    
    # Create model class
    model_class = type(name, (base_class,), namespace)
    
    return model_class


def create_model_from_protocols(
    *protocols: Type[Protocol],
    name: Optional[str] = None,
    additional_fields: Optional[Dict[str, Any]] = None,
    base_class: Type[ProtocolModel] = ProtocolModel,
) -> Type[ProtocolModel]:
    """
    Create a model from protocol classes (not IDs).
    
    Example:
        from pydapter.protocols.behaviors import Identifiable, Temporal
        
        Event = create_model_from_protocols(
            Identifiable,
            Temporal,
            name="Event",
            additional_fields={"title": StringField()}
        )
    """
    if not name:
        name = "_".join(p.__name__ for p in protocols) + "Model"
    
    protocol_ids = [p.__protocol_id__ for p in protocols]
    return create_protocol_model(name, *protocol_ids, additional_fields=additional_fields, base_class=base_class)


def extend_model(
    model_class: Type[ProtocolModel],
    *additional_protocols: str,
    name: Optional[str] = None,
    additional_fields: Optional[Dict[str, Any]] = None,
) -> Type[ProtocolModel]:
    """
    Extend an existing model with additional protocols.
    
    Example:
        BaseUser = create_protocol_model("BaseUser", "identifiable")
        User = extend_model(BaseUser, "temporal", "auditable", name="User")
    """
    # Get existing protocols
    existing_protocol_ids = [p.__protocol_id__ for p in model_class.__protocols__]
    
    # Combine with new protocols
    all_protocol_ids = existing_protocol_ids + list(additional_protocols)
    
    # Get existing additional fields
    existing_fields = {}
    if hasattr(model_class, "__schema__"):
        for field_name, schema_field in model_class.__schema__.fields.items():
            # Check if field comes from a protocol
            is_protocol_field = any(
                field_name in p.get_all_fields()
                for p in model_class.__protocols__
            )
            if not is_protocol_field:
                existing_fields[field_name] = schema_field.template
    
    # Merge additional fields
    all_fields = {**existing_fields, **(additional_fields or {})}
    
    # Create new model
    if not name:
        name = model_class.__name__ + "Extended"
    
    return create_protocol_model(
        name,
        *all_protocol_ids,
        additional_fields=all_fields,
        base_class=model_class,
    )