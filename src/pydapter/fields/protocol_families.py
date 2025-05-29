"""Protocol Field Families - Field templates for protocol integration.

This module provides field families that correspond to pydapter protocols,
enabling easy creation of models that implement specific protocol interfaces.
"""

from __future__ import annotations

from pydapter.fields.common_templates import (
    CREATED_AT_TEMPLATE,
    CREATED_AT_TZ_TEMPLATE,
    ID_TEMPLATE,
    JSON_TEMPLATE,
    UPDATED_AT_TEMPLATE,
    UPDATED_AT_TZ_TEMPLATE,
)
from pydapter.fields.execution import Execution
from pydapter.fields.template import FieldTemplate

__all__ = (
    "ProtocolFieldFamilies",
    "create_protocol_model",
)


class ProtocolFieldFamilies:
    """Field families for pydapter protocol compliance.

    This class provides field template collections that match the requirements
    of various pydapter protocols. Using these families ensures your models
    will be compatible with protocol mixins and functionality.
    """

    # Identifiable protocol fields
    IDENTIFIABLE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE,
    }

    # Temporal protocol fields (naive datetime)
    TEMPORAL: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TEMPLATE,
        "updated_at": UPDATED_AT_TEMPLATE,
    }

    # Temporal protocol fields (timezone-aware)
    TEMPORAL_TZ: dict[str, FieldTemplate] = {
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
    }

    # Embeddable protocol fields
    EMBEDDABLE: dict[str, FieldTemplate] = {
        "embedding": FieldTemplate(
            base_type=list[float],
            description="Vector embedding",
            default_factory=list,
            json_schema_extra={"vector_dim": 1536},  # Default OpenAI dimension
        ),
    }

    # Invokable protocol fields
    INVOKABLE: dict[str, FieldTemplate] = {
        "execution": None,  # Will be defined below
    }

    # Cryptographical protocol fields
    CRYPTOGRAPHICAL: dict[str, FieldTemplate] = {
        "sha256": FieldTemplate(
            base_type=str,
            description="SHA256 hash of the content",
        ).as_nullable(),
    }

    # Event protocol base fields (combines multiple protocols)
    EVENT_BASE: dict[str, FieldTemplate] = {
        "id": ID_TEMPLATE.copy(frozen=True),  # Events have frozen IDs
        "created_at": CREATED_AT_TZ_TEMPLATE,
        "updated_at": UPDATED_AT_TZ_TEMPLATE,
        "event_type": FieldTemplate(
            base_type=str,
            description="Type of the event",
        ).as_nullable(),
        "content": FieldTemplate(
            base_type=str | dict | None,
            description="Content of the event",
            default=None,
        ),
        "request": JSON_TEMPLATE.copy(description="Request parameters"),
    }

    # Complete Event protocol fields (all protocols combined)
    EVENT_COMPLETE: dict[str, FieldTemplate] = {
        **EVENT_BASE,
        **EMBEDDABLE,
        **CRYPTOGRAPHICAL,
        "execution": None,  # Will be defined below
    }


# Define the execution template
_EXECUTION_TEMPLATE = FieldTemplate(
    base_type=Execution,
    description="Execution details",
    default_factory=Execution,
)

# Update the INVOKABLE family
ProtocolFieldFamilies.INVOKABLE["execution"] = _EXECUTION_TEMPLATE
ProtocolFieldFamilies.EVENT_COMPLETE["execution"] = _EXECUTION_TEMPLATE


def create_protocol_model(
    name: str,
    *protocols: str,
    timezone_aware: bool = True,
    base_fields: dict[str, FieldTemplate] | None = None,
    **extra_fields: FieldTemplate,
) -> type:
    """Create a model that implements specified protocols.

    This function creates a Pydantic model with fields required by the specified
    protocols. It automatically includes the appropriate field families and can
    be extended with custom fields.

    Args:
        name: Name for the generated model class
        *protocols: Protocol names to implement. Supported values:
            - "identifiable": Adds id field
            - "temporal": Adds created_at and updated_at fields
            - "embeddable": Adds embedding field
            - "invokable": Adds execution field
            - "cryptographical": Adds sha256 field
            - "event": Adds all Event protocol fields
        timezone_aware: If True, uses timezone-aware datetime fields (default: True)
        base_fields: Optional base field family to start with
        **extra_fields: Additional field templates to include

    Returns:
        A new Pydantic model class with protocol-compliant fields

    Examples:
        ```python
        # Create a model with ID and timestamps
        TrackedEntity = create_protocol_model(
            "TrackedEntity",
            "identifiable",
            "temporal",
        )

        # Create an event model with custom fields
        CustomEvent = create_protocol_model(
            "CustomEvent",
            "event",
            user_id=ID_TEMPLATE,
            action=FieldTemplate(base_type=str, description="User action"),
        )

        # Create an embeddable document
        Document = create_protocol_model(
            "Document",
            "identifiable",
            "temporal",
            "embeddable",
            title=NAME_TEMPLATE,
            content=FieldTemplate(base_type=str),
        )
        ```
    """
    from pydapter.fields.families import create_field_dict
    from pydapter.fields.types import create_model

    # Start with base fields if provided
    field_families = []
    if base_fields:
        field_families.append(base_fields)

    # Add protocol fields
    for protocol in protocols:
        protocol_lower = protocol.lower()

        if protocol_lower == "identifiable":
            field_families.append(ProtocolFieldFamilies.IDENTIFIABLE)
        elif protocol_lower == "temporal":
            if timezone_aware:
                field_families.append(ProtocolFieldFamilies.TEMPORAL_TZ)
            else:
                field_families.append(ProtocolFieldFamilies.TEMPORAL)
        elif protocol_lower == "embeddable":
            field_families.append(ProtocolFieldFamilies.EMBEDDABLE)
        elif protocol_lower == "invokable":
            field_families.append(ProtocolFieldFamilies.INVOKABLE)
        elif protocol_lower == "cryptographical":
            field_families.append(ProtocolFieldFamilies.CRYPTOGRAPHICAL)
        elif protocol_lower == "event":
            field_families.append(ProtocolFieldFamilies.EVENT_COMPLETE)
        else:
            raise ValueError(
                f"Unknown protocol: {protocol}. Supported protocols are: "
                f"identifiable, temporal, embeddable, invokable, cryptographical, event"
            )

    # Create field dictionary
    fields = create_field_dict(*field_families, **extra_fields)

    # Create and return the model
    return create_model(name, fields=fields)
