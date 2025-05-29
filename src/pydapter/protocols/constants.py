"""Protocol constants for type-safe protocol selection."""

from typing import Literal

# Protocol type literals for type checking
ProtocolType = Literal[
    "identifiable",
    "temporal",
    "embeddable",
    "invokable",
    "cryptographical",
]

# Protocol constants
IDENTIFIABLE: ProtocolType = "identifiable"
TEMPORAL: ProtocolType = "temporal"
EMBEDDABLE: ProtocolType = "embeddable"
INVOKABLE: ProtocolType = "invokable"
CRYPTOGRAPHICAL: ProtocolType = "cryptographical"

# Map protocol names to their corresponding mixin classes
PROTOCOL_MIXINS = {
    "identifiable": "IdentifiableMixin",
    "temporal": "TemporalMixin",
    "embeddable": "EmbeddableMixin",
    "invokable": "InvokableMixin",
    "cryptographical": "CryptographicalMixin",
}

# Export all constants
__all__ = [
    "ProtocolType",
    "IDENTIFIABLE",
    "TEMPORAL",
    "EMBEDDABLE",
    "INVOKABLE",
    "CRYPTOGRAPHICAL",
    "PROTOCOL_MIXINS",
]
