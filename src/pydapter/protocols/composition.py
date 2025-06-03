"""Protocol composition system with conflict resolution."""

from typing import Callable, Dict, List, Optional, Set, Type
from functools import lru_cache

from .core import Protocol, ProtocolMeta, protocol_registry
from ..fields import FieldTemplate


class ProtocolComposer:
    """
    Composes multiple protocols into a unified protocol.
    Handles field conflicts and behavior merging.
    """

    def __init__(self):
        self._composition_cache = {}

    def compose(
        self,
        *protocols: Type[Protocol],
        name: Optional[str] = None,
        resolve_conflicts: Optional[Callable[[str, FieldTemplate, FieldTemplate], FieldTemplate]] = None,
    ) -> Type[Protocol]:
        """
        Compose multiple protocols into one.
        
        Args:
            protocols: Protocol classes to compose
            name: Name for composed protocol
            resolve_conflicts: Function to resolve field conflicts
        
        Returns:
            New protocol class with combined fields and behaviors
        """
        # Check cache
        protocol_ids = frozenset(p.__protocol_id__ for p in protocols)
        if protocol_ids in self._composition_cache:
            return self._composition_cache[protocol_ids]

        # Generate name
        if not name:
            name = "_".join(p.__name__ for p in protocols)

        # Merge fields
        required_fields = {}
        optional_fields = {}
        conflicts = []

        for protocol in protocols:
            # Check required fields
            for field_name, field_template in protocol.__required_fields__.items():
                if field_name in required_fields:
                    conflicts.append(
                        (field_name, required_fields[field_name], field_template, protocol)
                    )
                else:
                    required_fields[field_name] = field_template

            # Check optional fields
            for field_name, field_template in protocol.__optional_fields__.items():
                if field_name in optional_fields or field_name in required_fields:
                    conflicts.append(
                        (
                            field_name,
                            optional_fields.get(field_name)
                            or required_fields.get(field_name),
                            field_template,
                            protocol,
                        )
                    )
                else:
                    optional_fields[field_name] = field_template

        # Resolve conflicts
        if conflicts:
            if resolve_conflicts:
                for field_name, existing, new, protocol in conflicts:
                    resolved = resolve_conflicts(field_name, existing, new)
                    if field_name in required_fields:
                        required_fields[field_name] = resolved
                    else:
                        optional_fields[field_name] = resolved
            else:
                # Default: use first definition (already in place)
                pass

        # Merge behaviors
        behaviors = []
        seen_behaviors = set()
        for protocol in protocols:
            for behavior in protocol.__behaviors__:
                if behavior not in seen_behaviors:
                    behaviors.append(behavior)
                    seen_behaviors.add(behavior)

        # Create composed protocol
        protocol_id = f"composed_{hash(protocol_ids) & 0xFFFFFFFF:08x}"

        # Create namespace with combined methods
        namespace = {
            "__protocol_id__": protocol_id,
            "__required_fields__": required_fields,
            "__optional_fields__": optional_fields,
            "__behaviors__": behaviors,
            "__composed_from__": protocols,
        }

        # Add behavior methods
        for protocol in protocols:
            for behavior in protocol.__behaviors__:
                if hasattr(protocol, behavior):
                    namespace[behavior] = getattr(protocol, behavior)

        # Create class
        composed_class = ProtocolMeta(name, (Protocol,), namespace)

        # Cache and register
        self._composition_cache[protocol_ids] = composed_class
        protocol_registry.register_composition(
            {p.__protocol_id__ for p in protocols}, composed_class
        )

        return composed_class

    def decompose(self, protocol: Type[Protocol]) -> List[Type[Protocol]]:
        """Get original protocols from a composed protocol."""
        return getattr(protocol, "__composed_from__", [protocol])

    def is_composed(self, protocol: Type[Protocol]) -> bool:
        """Check if a protocol is composed."""
        return hasattr(protocol, "__composed_from__")


# Global composer instance
_composer = ProtocolComposer()


@lru_cache(maxsize=128)
def compose_protocols(
    *protocol_ids: str, name: Optional[str] = None
) -> Type[Protocol]:
    """
    Compose protocols by their IDs.
    
    Example:
        Entity = compose_protocols("identifiable", "temporal", "auditable")
    """
    protocols = []
    for protocol_id in protocol_ids:
        protocol = ProtocolMeta.get_protocol(protocol_id)
        if not protocol:
            raise ValueError(f"Unknown protocol: {protocol_id}")
        protocols.append(protocol)

    return _composer.compose(*protocols, name=name)


def create_protocol(
    name: str, *behaviors: str, **fields: FieldTemplate
) -> Type[Protocol]:
    """
    Create a new protocol with fields and behaviors.
    
    Example:
        Rateable = create_protocol(
            "Rateable",
            "rate", "get_average_rating",
            rating=FloatField(min_value=0, max_value=5),
            rating_count=IntField(default=0),
        )
    """
    # Split fields into required and optional based on template config
    required_fields = {}
    optional_fields = {}

    for field_name, template in fields.items():
        if template.required:
            required_fields[field_name] = template
        else:
            optional_fields[field_name] = template

    # Create protocol class
    protocol_id = name.lower()
    namespace = {
        "__protocol_id__": protocol_id,
        "__required_fields__": required_fields,
        "__optional_fields__": optional_fields,
        "__behaviors__": list(behaviors),
    }

    # Create and register
    protocol_class = type(name, (Protocol,), namespace)
    protocol_registry.register(protocol_class)

    return protocol_class