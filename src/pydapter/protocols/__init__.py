"""Pydapter Protocol System - Composable protocols with integrated field definitions."""

from .core import Protocol, ProtocolMeta, ProtocolRegistry, protocol_registry
from .behaviors import (
    Identifiable,
    Temporal,
    Auditable,
    Versionable,
    SoftDeletable,
    Taggable,
    Searchable,
)
from .composition import ProtocolComposer, compose_protocols, create_protocol
from .factory import (
    ProtocolModel,
    create_protocol_model,
    create_model_from_protocols,
    extend_model,
)

# Keep existing imports for backward compatibility
from .base_model import *
from .registry import *
from .types import *
from .utils import *
from .constants import *
from .cryptographical import *
from .embeddable import *
from .event import *
from .identifiable import IdentifiableMixin
from .invokable import *
from .soft_deletable import SoftDeletableMixin
from .temporal import TemporalMixin
from .auditable import AuditableMixin

__all__ = [
    # Core
    "Protocol",
    "ProtocolMeta",
    "ProtocolRegistry",
    "protocol_registry",
    # Behaviors
    "Identifiable",
    "Temporal", 
    "Auditable",
    "Versionable",
    "SoftDeletable",
    "Taggable",
    "Searchable",
    # Composition
    "ProtocolComposer",
    "compose_protocols",
    "create_protocol",
    # Factory
    "ProtocolModel",
    "create_protocol_model",
    "create_model_from_protocols",
    "extend_model",
    # Legacy exports (kept for compatibility)
    "IdentifiableMixin",
    "TemporalMixin",
    "AuditableMixin",
    "SoftDeletableMixin",
    "create_base_model",
    "combine_with_mixins",
]