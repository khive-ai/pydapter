"""Pydapter Field System - High-performance field definitions for runtime model generation."""

from .core import Field, FieldSchema, ValidationProtocol
from .templates import (
    FieldTemplate,
    StringField,
    IntField,
    FloatField,
    BoolField,
    DateTimeField,
    UUIDField,
    DecimalField,
    ListField,
    DictField,
)
from .schema import Schema, SchemaBuilder, SchemaField, create_schema

# Keep existing imports for backward compatibility
from .types import *
from .builder import *
from .dts import *
from .embedding import *
from .execution import *
from .families import *
from .ids import *
from .params import *
from .protocol_families import *
from .template import *
from .validation_patterns import *
from .common_templates import *

__all__ = [
    # Core
    "Field",
    "FieldSchema", 
    "ValidationProtocol",
    # Templates
    "FieldTemplate",
    "StringField",
    "IntField",
    "FloatField",
    "BoolField",
    "DateTimeField",
    "UUIDField",
    "DecimalField",
    "ListField",
    "DictField",
    # Schema
    "Schema",
    "SchemaBuilder",
    "SchemaField",
    "create_schema",
    # Legacy exports (kept for compatibility)
    "FieldFactory",
    "FieldBuilder",
    "FieldDefinition",
    "ProtocolFieldFamily",
    "ENTITY_FIELDS",
    "AUDIT_FIELDS",
    "TEMPORAL_FIELDS",
    "SOFT_DELETE_FIELDS",
]