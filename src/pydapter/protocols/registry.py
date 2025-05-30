from pydapter.protocols.auditable import AuditableMixin
from pydapter.protocols.cryptographical import CryptographicalMixin
from pydapter.protocols.embeddable import EmbeddableMixin
from pydapter.protocols.identifiable import IdentifiableMixin
from pydapter.protocols.invokable import InvokableMixin
from pydapter.protocols.soft_deletable import SoftDeletableMixin
from pydapter.protocols.temporal import TemporalMixin

# Mapping of protocol names to actual mixin classes
_MIXIN_CLASSES = {
    "identifiable": IdentifiableMixin,
    "temporal": TemporalMixin,
    "embeddable": EmbeddableMixin,
    "invokable": InvokableMixin,
    "cryptographical": CryptographicalMixin,
    "auditable": AuditableMixin,
    "soft_deletable": SoftDeletableMixin,
}


def register_mixin(protocol_name: str, mixin_class: type) -> None:
    """
    Register a new mixin class for a protocol.

    Args:
        protocol_name: The name of the protocol (e.g., "identifiable").
        mixin_class: The mixin class to register.
    """
    _MIXIN_CLASSES[protocol_name.lower()] = mixin_class


def get_mixin_registry() -> dict[str, type]:
    """
    Get the registry of mixin classes for protocols.

    Returns:
        A dictionary mapping protocol names to their corresponding mixin classes.
    """
    return _MIXIN_CLASSES


__all__ = (
    "register_mixin",
    "get_mixin_registry",
)
