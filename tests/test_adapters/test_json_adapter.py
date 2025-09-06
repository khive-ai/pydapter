#!/usr/bin/env python3
"""Test script for JSON adapter with new lionagi exception pattern."""

from pydantic import BaseModel

from pydapter.adapters.json_ import JsonAdapter
from pydapter.exceptions import ParseError, ValidationError


class Person(BaseModel):
    name: str
    age: int


def test_successful_operations():
    """Test normal JSON operations work."""
    print("=== Testing successful operations ===")

    # Single object
    json_data = '{"name": "John", "age": 30}'
    person = JsonAdapter.from_obj(Person, json_data)
    print(f"✓ Parsed single: {person}")

    # Array
    json_array = '[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]'
    people = JsonAdapter.from_obj(Person, json_array, many=True)
    print(f"✓ Parsed array: {people}")

    # Convert to JSON
    json_output = JsonAdapter.to_obj(person)
    print(f"✓ Generated JSON: {json_output}")


def test_validation_errors():
    """Test that validation errors are properly wrapped."""
    print("\n=== Testing validation errors ===")

    # Invalid data type
    try:
        JsonAdapter.from_obj(Person, '{"name": "John", "age": "not_a_number"}')
    except ValidationError as e:
        print(f"✓ ValidationError caught: {e.message}")
        print(f"  Details: {e.details}")
        print(f"  Status code: {e.status_code}")
        print(f"  Has cause: {e.get_cause() is not None}")
        print(f"  Error dict: {e.to_dict()}")

    # Wrong structure for many=True
    try:
        JsonAdapter.from_obj(Person, '{"name": "John", "age": 30}', many=True)
    except ValidationError as e:
        print(f"✓ Array validation error: {e.message}")
        print(f"  Details: {e.details}")


def test_parse_errors():
    """Test that parse errors are properly wrapped."""
    print("\n=== Testing parse errors ===")

    # Invalid JSON
    try:
        JsonAdapter.from_obj(Person, '{"name": "John", "age":}')
    except ParseError as e:
        print(f"✓ ParseError caught: {e.message}")
        print(f"  Details: {e.details}")
        print(f"  Status code: {e.status_code}")
        print(f"  Has cause: {e.get_cause() is not None}")


def test_custom_adapt_methods():
    """Test with custom adapt methods."""
    print("\n=== Testing custom adapt methods ===")

    class CustomClass:
        def __init__(self, name: str, age: int):
            self.name = name
            self.age = age

        @classmethod
        def from_dict(cls, data):
            return cls(data["name"], data["age"])

        def to_dict(self):
            return {"name": self.name, "age": self.age}

        def __repr__(self):
            return f"CustomClass(name={self.name}, age={self.age})"

    # Test with custom methods
    json_data = '{"name": "Custom", "age": 99}'
    try:
        obj = JsonAdapter.from_obj(CustomClass, json_data, adapt_meth="from_dict")
        print(f"✓ Custom from_dict: {obj}")

        json_output = JsonAdapter.to_obj(obj, adapt_meth="to_dict")
        print(f"✓ Custom to_dict: {json_output}")
    except Exception as e:
        print(f"✗ Custom method error: {e}")


if __name__ == "__main__":
    test_successful_operations()
    test_validation_errors()
    test_parse_errors()
    test_custom_adapt_methods()
    print("\n=== All tests completed ===")
