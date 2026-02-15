"""
Tests for YAML adapter functionality and error handling.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from pydantic import BaseModel

from pydapter.adapters.yaml_ import YamlAdapter
from pydapter.core import Adaptable
from pydapter.exceptions import ParseError, ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError


class TestYamlAdapterBasic:
    """Basic YAML adapter functionality tests."""

    def test_simple_yaml_parsing(self):
        """Test parsing simple YAML data."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        yaml_data = """
id: 1
name: test
value: 42.5
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    def test_yaml_array_many_true(self):
        """Test parsing YAML array with many=True."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        yaml_data = """
- id: 1
  name: test1
  value: 42.5
- id: 2
  name: test2
  value: 43.5
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml", many=True)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "test1"
        assert result[1].id == 2
        assert result[1].name == "test2"

    def test_yaml_from_bytes(self):
        """Test parsing YAML from bytes."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        yaml_bytes = b"id: 1\nname: test\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_bytes, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    def test_yaml_from_file(self):
        """Test parsing YAML from file."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Create temporary YAML file
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("id: 1\nname: test\nvalue: 42.5")
            temp_path = Path(f.name)

        try:
            result = TestModel.adapt_from(temp_path, obj_key="yaml")
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5
        finally:
            temp_path.unlink()

    def test_yaml_roundtrip(self):
        """Test YAML roundtrip serialization."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        original = TestModel(id=1, name="test", value=42.5)
        yaml_str = original.adapt_to(obj_key="yaml")
        restored = TestModel.adapt_from(yaml_str, obj_key="yaml")

        assert restored == original
        assert restored.id == 1
        assert restored.name == "test"
        assert restored.value == 42.5

    def test_yaml_roundtrip_many(self):
        """Test YAML roundtrip with many=True."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        originals = [
            TestModel(id=1, name="test1", value=42.5),
            TestModel(id=2, name="test2", value=43.5),
        ]
        yaml_str = YamlAdapter.to_obj(originals, many=True)
        restored = YamlAdapter.from_obj(TestModel, yaml_str, many=True)

        assert len(restored) == 2
        assert restored[0] == originals[0]
        assert restored[1] == originals[1]


class TestYamlAdapterErrors:
    """Tests for YAML adapter error handling."""

    def test_invalid_yaml(self):
        """Test handling of invalid YAML input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test invalid YAML (improper indentation)
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("id: 1\n  name: test\nvalue: 42.5", obj_key="yaml")
        assert "yaml" in str(exc_info.value).lower()

    def test_empty_yaml(self):
        """Test handling of empty YAML input."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test empty string
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("", obj_key="yaml")
        assert "Empty YAML content" in str(exc_info.value)

        # Test whitespace only
        with pytest.raises(ParseError) as exc_info:
            TestModel.adapt_from("   \n   ", obj_key="yaml")
        assert "Empty YAML content" in str(exc_info.value)

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test missing required fields
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from("id: 1\nname: test", obj_key="yaml")
        # Check that the error mentions the missing fields
        assert "value" in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test handling of invalid field types."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test invalid field types
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from("id: not_an_int\nname: test\nvalue: 42.5", obj_key="yaml")
        # Check that the error mentions the invalid field
        assert "id" in str(exc_info.value)

    def test_yaml_file_not_found(self):
        """Test handling of non-existent YAML file."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test non-existent file - should raise ResourceError
        with pytest.raises(ResourceError) as exc_info:
            TestModel.adapt_from(Path("nonexistent.yaml"), obj_key="yaml")
        assert "nonexistent.yaml" in str(exc_info.value)

    def test_yaml_array_with_many_false(self):
        """Test handling of YAML array with many=False."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test YAML array with many=False - should fail validation
        yaml_array = """
- id: 1
  name: test
  value: 42.5
"""
        with pytest.raises(AdapterValidationError) as exc_info:
            TestModel.adapt_from(yaml_array, obj_key="yaml", many=False)
        # Error should mention that it received a list instead of dict
        assert "list" in str(exc_info.value).lower() or "array" in str(exc_info.value).lower()


class TestYamlAdapterFeatures:
    """Tests for YAML-specific features."""

    def test_yaml_multiline_strings(self):
        """Test YAML multiline strings."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            description: str

        TestModel.register_adapter(YamlAdapter)

        # Test literal block scalar (preserves newlines)
        yaml_data = """
id: 1
name: test
description: |
  This is a multiline
  description with
  preserved newlines
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert "multiline" in result.description
        assert "\n" in result.description

        # Test folded block scalar (folds newlines into spaces)
        yaml_data = """
id: 1
name: test
description: >
  This is a multiline
  description with
  folded newlines
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert "multiline" in result.description

    def test_yaml_unicode_characters(self):
        """Test handling of Unicode characters."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test YAML with Unicode characters (Chinese, emoji)
        yaml_data = "id: 1\nname: 测试 😊\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.name == "测试 😊"

        # Test roundtrip with Unicode
        yaml_str = result.adapt_to(obj_key="yaml")
        restored = TestModel.adapt_from(yaml_str, obj_key="yaml")
        assert restored.name == "测试 😊"

    def test_yaml_nested_structures(self):
        """Test YAML nested structures."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(Adaptable, BaseModel):
            id: int
            name: str
            address: Address

        Person.register_adapter(YamlAdapter)

        yaml_data = """
id: 1
name: John
address:
  street: 123 Main St
  city: NYC
"""
        result = Person.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "John"
        assert result.address.street == "123 Main St"
        assert result.address.city == "NYC"

    def test_yaml_lists_and_dicts(self):
        """Test YAML lists and dictionaries."""

        class TestModel(Adaptable, BaseModel):
            id: int
            tags: list[str]
            metadata: dict[str, str]

        TestModel.register_adapter(YamlAdapter)

        yaml_data = """
id: 1
tags:
  - python
  - yaml
  - testing
metadata:
  author: test
  version: '1.0'
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.tags == ["python", "yaml", "testing"]
        assert result.metadata == {"author": "test", "version": "1.0"}

    def test_yaml_null_values(self):
        """Test YAML null values."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str | None
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Test explicit null
        yaml_data = "id: 1\nname: null\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name is None
        assert result.value == 42.5

        # Test tilde null
        yaml_data = "id: 1\nname: ~\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name is None
        assert result.value == 42.5

    def test_yaml_boolean_values(self):
        """Test YAML boolean values."""

        class TestModel(Adaptable, BaseModel):
            id: int
            active: bool
            enabled: bool

        TestModel.register_adapter(YamlAdapter)

        # Test various boolean representations
        yaml_data = "id: 1\nactive: true\nenabled: yes"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.active is True
        assert result.enabled is True

        yaml_data = "id: 1\nactive: false\nenabled: no"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.active is False
        assert result.enabled is False

    def test_yaml_comments(self):
        """Test YAML comments are ignored."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        yaml_data = """
# This is a comment
id: 1  # Inline comment
name: test  # Another comment
value: 42.5
# Final comment
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    def test_yaml_anchors_and_aliases(self):
        """Test YAML anchors and aliases."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            description: str

        TestModel.register_adapter(YamlAdapter)

        # YAML with anchors and aliases
        yaml_data = """
id: 1
name: &ref_name test
description: *ref_name
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test"
        assert result.description == "test"  # Alias resolves to same value


class TestYamlAdapterEdgeCases:
    """Tests for edge cases in YAML adapter."""

    def test_empty_collections(self):
        """Test handling of empty collections."""

        class TestModel(Adaptable, BaseModel):
            id: int
            tags: list[str]
            metadata: dict[str, str]

        TestModel.register_adapter(YamlAdapter)

        yaml_data = "id: 1\ntags: []\nmetadata: {}"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.tags == []
        assert result.metadata == {}

    def test_yaml_empty_list_many_true(self):
        """Test handling of empty array with many=True."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Empty array
        yaml_data = "[]"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml", many=True)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_boundary_values(self):
        """Test handling of boundary values."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        # Very large integer
        yaml_data = "id: 9223372036854775807\nname: test\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 9223372036854775807

        # Very small float
        yaml_data = "id: 1\nname: test\nvalue: 1e-308"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.value == 1e-308

    def test_very_long_strings(self):
        """Test handling of very long strings."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        long_name = "x" * 10000
        yaml_data = f"id: 1\nname: '{long_name}'\nvalue: 42.5"
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert len(result.name) == 10000
        assert result.name == long_name

    def test_yaml_special_characters_in_strings(self):
        """Test YAML special characters in strings."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            description: str

        TestModel.register_adapter(YamlAdapter)

        # Strings with colons, quotes, etc.
        yaml_data = """
id: 1
name: 'test: value'
description: "it's a test"
"""
        result = TestModel.adapt_from(yaml_data, obj_key="yaml")
        assert result.id == 1
        assert result.name == "test: value"
        assert result.description == "it's a test"

    def test_yaml_serialization_options(self):
        """Test YAML serialization with custom options."""

        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        TestModel.register_adapter(YamlAdapter)

        model = TestModel(id=1, name="test", value=42.5)

        # Test with default options
        yaml_str = model.adapt_to(obj_key="yaml")
        assert "id: 1" in yaml_str
        assert "name: test" in yaml_str

        # Test with flow style
        yaml_str = YamlAdapter.to_obj(model, default_flow_style=True)
        assert yaml_str  # Just verify it produces output

    def test_yaml_direct_adapter_usage(self):
        """Test using YamlAdapter directly without Adaptable."""

        class TestModel(BaseModel):
            id: int
            name: str
            value: float

        yaml_data = "id: 1\nname: test\nvalue: 42.5"
        result = YamlAdapter.from_obj(TestModel, yaml_data)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

        yaml_str = YamlAdapter.to_obj(result)
        assert "id: 1" in yaml_str

    def test_yaml_custom_adapt_methods(self):
        """Test YAML adapter with custom adaptation methods."""

        class TestModel(BaseModel):
            id: int
            name: str
            value: float

        yaml_data = "id: 1\nname: test\nvalue: 42.5"

        # Use model_validate_json (although this is YAML, testing the parameter works)
        result = YamlAdapter.from_obj(TestModel, yaml_data, adapt_meth="model_validate")
        assert result.id == 1

        # Use model_dump for serialization
        yaml_str = YamlAdapter.to_obj(result, adapt_meth="model_dump")
        assert "id: 1" in yaml_str
