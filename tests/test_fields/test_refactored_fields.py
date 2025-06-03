"""Tests for the refactored field system."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Optional

from pydapter.fields import (
    Field,
    FieldSchema,
    ValidationProtocol,
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
    Schema,
    SchemaBuilder,
    create_schema,
)


class TestFieldCore:
    """Test core field functionality."""

    def test_field_creation(self):
        """Test basic field creation."""
        schema = FieldSchema(name="test", type=str, required=True)
        field = Field(schema)
        
        assert field.name == "test"
        assert field.type == str
        assert field.metadata == {}

    def test_field_descriptor_behavior(self):
        """Test field descriptor get/set/delete."""
        schema = FieldSchema(name="name", type=str, required=True)
        field = Field(schema)
        
        class Model:
            name = field
        
        # Test set
        obj = Model()
        obj.name = "test"
        assert obj.name == "test"
        
        # Test validation on set
        with pytest.raises(ValueError):
            obj.name = None
        
        # Test delete
        del obj.name
        assert not hasattr(obj, "name")

    def test_field_validation(self):
        """Test field validation."""
        schema = FieldSchema(name="age", type=int, required=True)
        field = Field(schema)
        
        # Valid values
        assert field.validate(10) == 10
        assert field.validate("20") == 20  # Type coercion
        
        # Invalid values
        with pytest.raises(ValueError):
            field.validate(None)
        
        with pytest.raises(ValueError):
            field.validate("not a number")

    def test_field_optional_with_default(self):
        """Test optional fields with defaults."""
        schema = FieldSchema(
            name="count",
            type=int,
            required=False,
            default=0
        )
        field = Field(schema)
        
        assert field.validate(None) == 0
        assert field.validate(5) == 5

    def test_field_callable_default(self):
        """Test fields with callable defaults."""
        def make_list():
            return []
        
        schema = FieldSchema(
            name="items",
            type=list,
            required=False,
            default=make_list
        )
        field = Field(schema)
        
        class Model:
            items = field
        
        obj1 = Model()
        obj2 = Model()
        
        # Each instance should get its own list
        obj1.items.append(1)
        assert obj1.items == [1]
        assert obj2.items == []

    def test_field_serialization(self):
        """Test field serialization."""
        schema = FieldSchema(name="value", type=str)
        field = Field(schema)
        
        # Primitives
        assert field.serialize("test") == "test"
        assert field.serialize(123) == 123
        assert field.serialize(True) is True
        assert field.serialize(None) is None
        
        # Complex types
        assert field.serialize(datetime(2024, 1, 1)) == "2024-01-01 00:00:00"


class TestValidationProtocol:
    """Test custom validators."""

    def test_custom_validator(self):
        """Test creating custom validators."""
        class RangeValidator(ValidationProtocol):
            def __init__(self, min_val, max_val):
                self.min_val = min_val
                self.max_val = max_val
            
            def validate(self, value, field):
                if value < self.min_val or value > self.max_val:
                    raise ValueError(f"Value must be between {self.min_val} and {self.max_val}")
                return value
            
            @property
            def error_message(self):
                return f"Value out of range ({self.min_val}-{self.max_val})"
        
        schema = FieldSchema(
            name="score",
            type=int,
            validators=(RangeValidator(0, 100),)
        )
        field = Field(schema)
        
        assert field.validate(50) == 50
        
        with pytest.raises(ValueError) as exc_info:
            field.validate(150)
        assert "between 0 and 100" in str(exc_info.value)


class TestFieldTemplates:
    """Test field template system."""

    def test_string_field(self):
        """Test StringField template."""
        # Basic string field
        field = StringField(required=True).create_field("name")
        assert field.validate("test") == "test"
        
        # With constraints
        field = StringField(min_length=3, max_length=10).create_field("username")
        assert field.validate("user") == "user"
        
        with pytest.raises(ValueError):
            field.validate("ab")  # Too short
        
        with pytest.raises(ValueError):
            field.validate("verylongusername")  # Too long
        
        # With pattern
        field = StringField(pattern=r"^\d{3}-\d{4}$").create_field("phone")
        assert field.validate("123-4567") == "123-4567"
        
        with pytest.raises(ValueError):
            field.validate("1234567")

    def test_numeric_fields(self):
        """Test numeric field templates."""
        # IntField
        int_field = IntField(min_value=0, max_value=100).create_field("age")
        assert int_field.validate(25) == 25
        assert int_field.validate("30") == 30  # Type coercion
        
        with pytest.raises(ValueError):
            int_field.validate(-5)
        
        with pytest.raises(ValueError):
            int_field.validate(150)
        
        # FloatField
        float_field = FloatField(min_value=0.0, max_value=1.0).create_field("score")
        assert float_field.validate(0.5) == 0.5
        assert float_field.validate("0.75") == 0.75
        
        with pytest.raises(ValueError):
            float_field.validate(1.5)

    def test_datetime_field(self):
        """Test DateTimeField template."""
        # Timezone aware
        field = DateTimeField(timezone_aware=True).create_field("created_at")
        
        # Parse from string
        dt = field.validate("2024-01-01T12:00:00+00:00")
        assert dt.tzinfo is not None
        
        # Add timezone if missing
        naive_dt = datetime(2024, 1, 1, 12, 0)
        aware_dt = field.validate(naive_dt)
        assert aware_dt.tzinfo == timezone.utc
        
        # Timezone naive
        field = DateTimeField(timezone_aware=False).create_field("local_time")
        dt = field.validate(datetime.now(timezone.utc))
        assert dt.tzinfo is None

    def test_uuid_field(self):
        """Test UUIDField template."""
        # Auto-generate
        field = UUIDField(auto_generate=True).create_field("id")
        schema = field._schema
        assert callable(schema.default)
        assert isinstance(schema.default(), uuid.UUID)
        
        # Parse from string
        field = UUIDField(auto_generate=False).create_field("external_id")
        test_uuid = uuid.uuid4()
        assert field.validate(str(test_uuid)) == test_uuid

    def test_collection_fields(self):
        """Test ListField and DictField."""
        # ListField
        list_field = ListField(item_type=int).create_field("numbers")
        assert list_field.validate([1, 2, 3]) == [1, 2, 3]
        
        # DictField
        dict_field = DictField(key_type=str, value_type=int).create_field("scores")
        assert dict_field.validate({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_field_template_composition(self):
        """Test composing field templates."""
        # Create base template
        base = StringField(min_length=3)
        
        # Create variations
        optional = base.as_optional(default="")
        with_metadata = base.with_metadata(db_column="user_name", index=True)
        
        # Test optional
        field = optional.create_field("nickname")
        assert not field._schema.required
        assert field._schema.default == ""
        
        # Test metadata
        field = with_metadata.create_field("username")
        assert field.metadata["db_column"] == "user_name"
        assert field.metadata["index"] is True


class TestSchema:
    """Test schema system."""

    def test_schema_creation(self):
        """Test creating schemas."""
        schema = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(required=True),
            email=StringField(required=True),
            age=IntField(min_value=0),
        )
        
        assert schema.name == "User"
        assert len(schema.fields) == 4
        assert "id" in schema.field_names
        assert "name" in schema.required_fields
        assert "email" in schema.required_fields

    def test_schema_builder(self):
        """Test SchemaBuilder fluent API."""
        schema = (SchemaBuilder("Product")
            .add_field("id", UUIDField())
            .add_field("name", StringField(required=True))
            .add_field("price", DecimalField(max_digits=10, decimal_places=2))
            .add_field("tags", ListField(item_type=str))
            .with_metadata({"table": "products", "schema": "public"})
            .build()
        )
        
        assert schema.name == "Product"
        assert len(schema.fields) == 4
        assert schema.metadata["table"] == "products"

    def test_schema_merge(self):
        """Test merging schemas."""
        base = create_schema(
            "Base",
            id=UUIDField(),
            created_at=DateTimeField(auto_now_add=True),
        )
        
        extended = create_schema(
            "Extended",
            name=StringField(required=True),
            value=FloatField(),
        )
        
        merged = base.merge(extended, name="Combined")
        
        assert merged.name == "Combined"
        assert len(merged.fields) == 4
        assert "id" in merged.field_names
        assert "created_at" in merged.field_names
        assert "name" in merged.field_names
        assert "value" in merged.field_names

    def test_schema_select(self):
        """Test selecting fields from schema."""
        full_schema = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(),
            email=StringField(),
            password=StringField(),
            created_at=DateTimeField(),
        )
        
        public_schema = full_schema.select(["id", "name", "email"], name="PublicUser")
        
        assert public_schema.name == "PublicUser"
        assert len(public_schema.fields) == 3
        assert "password" not in public_schema.field_names

    def test_schema_extend(self):
        """Test extending schema with new fields."""
        base = create_schema(
            "Base",
            id=UUIDField(),
            name=StringField(),
        )
        
        extended = base.extend(
            email=StringField(required=True),
            active=BoolField(default=True),
        )
        
        assert len(extended.fields) == 4
        assert "email" in extended.field_names
        assert "active" in extended.field_names

    def test_schema_field_creation(self):
        """Test creating field instances from schema."""
        schema = create_schema(
            "Test",
            name=StringField(min_length=3),
            age=IntField(min_value=0, max_value=150),
        )
        
        fields = schema.create_fields()
        
        assert isinstance(fields["name"], Field)
        assert isinstance(fields["age"], Field)
        
        # Test that fields work correctly
        assert fields["name"].validate("John") == "John"
        assert fields["age"].validate(25) == 25
        
        with pytest.raises(ValueError):
            fields["name"].validate("Jo")  # Too short
        
        with pytest.raises(ValueError):
            fields["age"].validate(-5)  # Negative age


class TestFieldIntegration:
    """Integration tests for field system."""

    def test_model_with_fields(self):
        """Test using fields in a model class."""
        schema = create_schema(
            "Person",
            id=UUIDField(auto_generate=True),
            name=StringField(required=True, min_length=2),
            age=IntField(min_value=0, max_value=150),
            email=StringField(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
            active=BoolField(default=True),
            created_at=DateTimeField(auto_now_add=True),
        )
        
        class Person:
            def __init__(self, **kwargs):
                # Create and assign fields
                for field_name, field in schema.create_fields().items():
                    setattr(self.__class__, field_name, field)
                
                # Initialize values
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        # Create instance
        person = Person(
            name="John Doe",
            age=30,
            email="john@example.com"
        )
        
        # Check values
        assert person.name == "John Doe"
        assert person.age == 30
        assert person.email == "john@example.com"
        assert person.active is True  # Default
        assert isinstance(person.id, uuid.UUID)  # Auto-generated
        assert isinstance(person.created_at, datetime)  # Auto-generated
        
        # Test validation
        with pytest.raises(ValueError):
            person.age = 200  # Too old
        
        with pytest.raises(ValueError):
            person.email = "invalid-email"

    def test_schema_hash_and_equality(self):
        """Test schema hashing and equality."""
        schema1 = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(),
        )
        
        schema2 = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(),
        )
        
        schema3 = create_schema(
            "User",
            id=UUIDField(),
            name=StringField(),
            email=StringField(),  # Different fields
        )
        
        # Same definition should be equal
        assert schema1 == schema2
        assert hash(schema1) == hash(schema2)
        
        # Different fields should not be equal
        assert schema1 != schema3
        assert hash(schema1) != hash(schema3)