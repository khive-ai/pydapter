"""Schema system for dynamic model generation."""

from typing import Any, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field as dataclass_field
from functools import cached_property
import hashlib

from .core import Field
from .templates import FieldTemplate

T = TypeVar("T")


@dataclass(frozen=True)
class SchemaField:
    """Schema field definition."""

    name: str
    template: FieldTemplate
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)


class Schema:
    """
    Immutable schema definition for model generation.
    Schemas are the blueprint for creating dynamic models.
    """

    def __init__(
        self,
        name: str,
        fields: Dict[str, SchemaField],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.fields = fields
        self.metadata = metadata or {}
        self._hash = None

    @cached_property
    def field_names(self) -> List[str]:
        """Get ordered field names."""
        return list(self.fields.keys())

    @cached_property
    def required_fields(self) -> List[str]:
        """Get required field names."""
        return [
            name
            for name, field in self.fields.items()
            if field.template.required
        ]

    @cached_property
    def optional_fields(self) -> List[str]:
        """Get optional field names."""
        return [
            name
            for name, field in self.fields.items()
            if not field.template.required
        ]

    def create_fields(self) -> Dict[str, Field]:
        """Create field instances from schema."""
        return {
            name: schema_field.template.create_field(name)
            for name, schema_field in self.fields.items()
        }

    def merge(self, other: "Schema", name: Optional[str] = None) -> "Schema":
        """Merge two schemas into a new schema."""
        merged_fields = {**self.fields, **other.fields}
        merged_metadata = {**self.metadata, **other.metadata}
        merged_name = name or f"{self.name}_{other.name}"

        return Schema(merged_name, merged_fields, merged_metadata)

    def select(self, field_names: List[str], name: Optional[str] = None) -> "Schema":
        """Create a new schema with selected fields."""
        selected_fields = {
            name: self.fields[name]
            for name in field_names
            if name in self.fields
        }

        new_name = name or f"{self.name}_subset"
        return Schema(new_name, selected_fields, self.metadata.copy())

    def extend(self, **fields: FieldTemplate) -> "Schema":
        """Extend schema with new fields."""
        extended_fields = self.fields.copy()
        for field_name, template in fields.items():
            extended_fields[field_name] = SchemaField(field_name, template)
        
        return Schema(self.name, extended_fields, self.metadata.copy())

    def __hash__(self) -> int:
        """Hash for caching."""
        if self._hash is None:
            # Create stable hash from schema definition
            content = f"{self.name}:{sorted(self.fields.items())}"
            self._hash = int(hashlib.sha256(content.encode()).hexdigest()[:16], 16)
        return self._hash

    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Schema):
            return False
        return (
            self.name == other.name
            and self.fields == other.fields
            and self.metadata == other.metadata
        )


class SchemaBuilder:
    """
    Fluent builder for creating schemas with intuitive API.
    
    Example:
        schema = (SchemaBuilder("User")
            .add_field("id", UUIDField())
            .add_field("name", StringField(required=True))
            .add_field("email", EmailField())
            .add_field("created_at", DateTimeField(auto_now_add=True))
            .with_metadata({"table": "users"})
            .build()
        )
    """

    def __init__(self, name: str):
        self.name = name
        self.fields: Dict[str, SchemaField] = {}
        self.metadata: Dict[str, Any] = {}

    def add_field(
        self,
        name: str,
        template: FieldTemplate,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SchemaBuilder":
        """Add a field to the schema."""
        self.fields[name] = SchemaField(name, template, metadata or {})
        return self

    def add_fields(self, fields: Dict[str, FieldTemplate]) -> "SchemaBuilder":
        """Add multiple fields at once."""
        for name, template in fields.items():
            self.add_field(name, template)
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "SchemaBuilder":
        """Add metadata to the schema."""
        self.metadata.update(metadata)
        return self

    def extend(self, schema: Schema) -> "SchemaBuilder":
        """Extend with fields from another schema."""
        self.fields.update(schema.fields)
        return self

    def build(self) -> Schema:
        """Build the final schema."""
        return Schema(self.name, self.fields.copy(), self.metadata.copy())


def create_schema(name: str, **fields: FieldTemplate) -> Schema:
    """
    Create a schema with field templates.
    
    Example:
        schema = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(required=True),
            email=EmailField(),
        )
    """
    builder = SchemaBuilder(name)
    for field_name, template in fields.items():
        builder.add_field(field_name, template)
    return builder.build()