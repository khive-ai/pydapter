"""
Comprehensive unit tests for CSV adapter with focus on error handling patterns.
Tests the recent fixes to ensure consistent error handling using from_adapter pattern.
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from pydapter.adapters.csv_ import CsvAdapter
from pydapter.exceptions import ParseError, ResourceError, ValidationError


class Person(BaseModel):
    """Test model for CSV adapter testing."""

    name: str
    age: int
    email: str = "default@example.com"


class StrictPerson(BaseModel):
    """Test model with strict validation for testing."""

    name: str
    age: int

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, dict) and data.get("name") == "INVALID":
            raise ValueError("Name cannot be INVALID")
        return super().model_validate(data)


class TestCsvAdapterErrorHandling:
    """Test suite focusing on error handling patterns in CSV adapter."""

    def test_from_adapter_pattern_usage(self):
        """Verify all exceptions use from_adapter pattern correctly."""
        # Test ParseError from empty content
        with pytest.raises(ParseError) as exc_info:
            CsvAdapter.from_obj(Person, "")

        error = exc_info.value
        assert hasattr(error, "details")
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Empty CSV content" in error.message
        assert hasattr(error, "__cause__") or error.get_cause() is None

    def test_resource_error_file_not_found(self):
        """Test ResourceError when file cannot be read."""
        non_existent_path = Path("/non/existent/file.csv")

        with pytest.raises(ResourceError) as exc_info:
            CsvAdapter.from_obj(Person, non_existent_path)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Failed to read CSV file" in error.message
        assert error.get_cause() is not None  # Should have cause from file operation
        assert error.status_code == 404

    def test_parse_error_empty_content(self):
        """Test ParseError for empty CSV content."""
        test_cases = ["", "   ", "\n\n", "\t\t"]

        for empty_content in test_cases:
            with pytest.raises(ParseError) as exc_info:
                CsvAdapter.from_obj(Person, empty_content)

            error = exc_info.value
            assert error.details.get("adapter_obj_key") == "csv"
            assert "Empty CSV content" in error.message
            assert error.status_code == 400

    def test_validation_error_wrong_headers(self):
        """Test ValidationError when CSV headers don't match model fields."""
        # CSV content where first row becomes headers but doesn't match model fields
        csv_content = "John,25,john@example.com\nJane,30,jane@example.com"

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Data conversion failed in row 1" in error.message
        assert error.status_code == 422
        assert error.details.get("row_number") == 1

    def test_validation_error_invalid_data_type(self):
        """Test ValidationError when data types don't match model."""
        csv_content = """name,age,email
John,not_a_number,john@example.com"""

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Data conversion failed in row 1" in error.message
        assert error.details.get("row_number") == 1
        assert error.details.get("row_data") is not None
        assert error.get_cause() is not None  # Should have cause from Pydantic
        assert error.status_code == 422

    def test_validation_error_missing_required_field(self):
        """Test ValidationError when required fields are missing."""
        csv_content = """name,email
John,john@example.com"""  # Missing age field

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Data conversion failed in row 1" in error.message
        assert error.get_cause() is not None

    def test_validation_error_with_strict_model(self):
        """Test ValidationError with custom model validation."""
        csv_content = """name,age
INVALID,25"""

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(StrictPerson, csv_content)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Data conversion failed in row 1" in error.message
        assert error.get_cause() is not None

    def test_validation_error_malformed_csv_content(self):
        """Test ValidationError when CSV content is malformed but parseable."""
        # CSV with unmatched quotes that gets parsed incorrectly
        csv_content = """name,age,email
"John,25,john@example.com
Jane,30,jane@example.com"""

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Data conversion failed in row 1" in error.message
        assert error.status_code == 422

    def test_parse_error_null_bytes_handling(self):
        """Test that NULL bytes are handled gracefully."""
        csv_content = "name,age,email\nJohn\x00,25,john@example.com"

        # Should not raise error - NULL bytes should be sanitized
        result = CsvAdapter.from_obj(Person, csv_content)
        assert len(result) == 1
        assert result[0].name == "John"  # NULL byte should be removed

    def test_to_obj_error_handling(self):
        """Test error handling in to_obj method."""

        # Create an object that will cause serialization issues
        class ProblematicModel:
            def model_dump(self):
                raise ValueError("Serialization failed")

        problematic_obj = ProblematicModel()

        with pytest.raises(ParseError) as exc_info:
            CsvAdapter.to_obj(problematic_obj)

        error = exc_info.value
        assert error.details.get("adapter_obj_key") == "csv"
        assert "Error generating CSV" in error.message
        assert error.get_cause() is not None

    def test_error_chaining_preservation(self):
        """Test that error chaining is properly preserved."""
        # Test with file that doesn't exist
        with pytest.raises(ResourceError) as exc_info:
            CsvAdapter.from_obj(Person, Path("/nonexistent/file.csv"))

        error = exc_info.value
        cause = error.get_cause()
        assert cause is not None
        assert isinstance(cause, (FileNotFoundError, OSError))

    def test_error_details_completeness(self):
        """Test that error details contain all expected information."""
        csv_content = """name,age,email
John,invalid_age,john@example.com"""

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        details = error.details

        # Check all expected details are present
        assert "adapter_obj_key" in details
        assert "row_data" in details
        assert "row_number" in details
        assert "adapt_method" in details
        assert details["adapter_obj_key"] == "csv"
        assert details["row_number"] == 1
        assert details["adapt_method"] == "model_validate"

    def test_multiple_row_errors(self):
        """Test that errors are reported for first failing row."""
        csv_content = """name,age,email
John,25,john@example.com
Jane,invalid_age,jane@example.com
Bob,35,bob@example.com"""

        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)

        error = exc_info.value
        # Should fail on row 2 (Jane with invalid age)
        assert error.details.get("row_number") == 2

    def test_success_path_many_true(self):
        """Test successful parsing with many=True."""
        csv_content = """name,age,email
John,25,john@example.com
Jane,30,jane@example.com"""

        result = CsvAdapter.from_obj(Person, csv_content, many=True)
        assert len(result) == 2
        assert result[0].name == "John"
        assert result[1].name == "Jane"

    def test_success_path_many_false(self):
        """Test successful parsing with many=False."""
        csv_content = """name,age,email
John,25,john@example.com"""

        result = CsvAdapter.from_obj(Person, csv_content, many=False)
        assert isinstance(result, Person)
        assert result.name == "John"

    def test_custom_csv_parameters(self):
        """Test error handling with custom CSV parameters."""
        # CSV with semicolon delimiter
        csv_content = """name;age;email
John;25;john@example.com"""

        result = CsvAdapter.from_obj(Person, csv_content, delimiter=";")
        assert len(result) == 1
        assert result[0].name == "John"

    def test_empty_csv_handling(self):
        """Test handling of CSV with only headers."""
        csv_content = """name,age,email"""

        result = CsvAdapter.from_obj(Person, csv_content, many=True)
        assert result == []

        result = CsvAdapter.from_obj(Person, csv_content, many=False)
        assert result is None

    def test_file_path_success(self):
        """Test successful reading from file path."""
        csv_content = """name,age,email
John,25,john@example.com"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = CsvAdapter.from_obj(Person, temp_path)
            assert len(result) == 1
            assert result[0].name == "John"
        finally:
            temp_path.unlink()

    def test_to_obj_success_path(self):
        """Test successful CSV generation."""
        person = Person(name="John", age=25, email="john@example.com")

        result = CsvAdapter.to_obj(person)
        assert "name,age,email" in result
        assert "John,25,john@example.com" in result

    def test_to_obj_empty_list(self):
        """Test CSV generation with empty list."""
        result = CsvAdapter.to_obj([])
        assert result == ""

    def test_to_obj_null_byte_sanitization(self):
        """Test that NULL bytes are sanitized in output."""
        person = Person(name="John\x00", age=25, email="john@example.com")

        result = CsvAdapter.to_obj(person)
        assert "\x00" not in result
        assert "John,25,john@example.com" in result

    def test_custom_adapt_methods(self):
        """Test with custom adaptation methods."""

        class CustomModel:
            def __init__(self, name, age):
                self.name = name
                self.age = age

            @classmethod
            def from_dict(cls, data):
                return cls(data["name"], int(data["age"]))

            def to_dict(self):
                return {"name": self.name, "age": self.age}

        csv_content = """name,age
John,25"""

        result = CsvAdapter.from_obj(CustomModel, csv_content, adapt_meth="from_dict")
        assert len(result) == 1
        assert result[0].name == "John"
        assert result[0].age == 25

    def test_exception_status_codes(self):
        """Test that exceptions have correct status codes."""
        # ParseError should have 400
        with pytest.raises(ParseError) as exc_info:
            CsvAdapter.from_obj(Person, "")
        assert exc_info.value.status_code == 400

        # ValidationError should have 422
        csv_content = """name,age,email
John,invalid_age,john@example.com"""
        with pytest.raises(ValidationError) as exc_info:
            CsvAdapter.from_obj(Person, csv_content)
        assert exc_info.value.status_code == 422

        # ResourceError should have 404
        with pytest.raises(ResourceError) as exc_info:
            CsvAdapter.from_obj(Person, Path("/nonexistent/file.csv"))
        assert exc_info.value.status_code == 404

    def test_error_to_dict_serialization(self):
        """Test that errors can be serialized to dict."""
        with pytest.raises(ParseError) as exc_info:
            CsvAdapter.from_obj(Person, "")

        error = exc_info.value
        error_dict = error.to_dict()

        assert "error" in error_dict
        assert "message" in error_dict
        assert "status_code" in error_dict
        assert "adapter_obj_key" in error_dict
        assert error_dict["adapter_obj_key"] == "csv"

    def test_error_to_dict_with_cause(self):
        """Test error serialization includes cause when requested."""
        with pytest.raises(ResourceError) as exc_info:
            CsvAdapter.from_obj(Person, Path("/nonexistent/file.csv"))

        error = exc_info.value
        error_dict = error.to_dict(include_cause=True)

        assert "cause" in error_dict
        assert error_dict["cause"] is not None
