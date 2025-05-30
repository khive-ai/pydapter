"""Protocol constants for type-safe protocol selection."""

from typing import Literal

# Protocol type literals for type checking
ProtocolType = Literal[
    "identifiable",
    "temporal",
    "embeddable",
    "invokable",
    "cryptographical",
    "soft_deletable",
    "auditable",
]

# Protocol constants
IDENTIFIABLE: ProtocolType = "identifiable"
TEMPORAL: ProtocolType = "temporal"
EMBEDDABLE: ProtocolType = "embeddable"
INVOKABLE: ProtocolType = "invokable"
CRYPTOGRAPHICAL: ProtocolType = "cryptographical"
AUDITABLE: ProtocolType = "auditable"
SOFT_DELETABLE: ProtocolType = "soft_deletable"

# Map protocol names to their corresponding mixin classes
PROTOCOL_MIXINS = {
    "identifiable": "IdentifiableMixin",
    "temporal": "TemporalMixin",
    "embeddable": "EmbeddableMixin",
    "invokable": "InvokableMixin",
    "cryptographical": "CryptographicalMixin",
    "auditable": "AuditableMixin",
    "soft_deletable": "SoftDeletableMixin",
}

# Export all constants
__all__ = [
    "ProtocolType",
    "IDENTIFIABLE",
    "TEMPORAL",
    "EMBEDDABLE",
    "INVOKABLE",
    "CRYPTOGRAPHICAL",
    "AUDITABLE",
    "SOFT_DELETABLE",
    "PROTOCOL_MIXINS",
]
