"""
Comprehensive tests for Pandas DataFrame and Series adapters.
"""

from datetime import datetime

import pandas as pd
from pydantic import BaseModel
import pytest

from pydapter.exceptions import ResourceError
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.pandas_ import DataFrameAdapter, SeriesAdapter

# ===== Test Models =====


class SimpleModel(BaseModel):
    """Simple model for basic tests."""

    id: int
    name: str
    value: float


class ComplexModel(BaseModel):
    """Complex model with various types."""

    id: int
    name: str
    value: float
    is_active: bool
    created_at: datetime
    optional_field: str | None = None


class StrictModel(BaseModel):
    """Model with strict validation."""

    id: int
    email: str
    score: float

    model_config = {"str_strip_whitespace": True}


# ===== DataFrameAdapter Tests =====


class TestDataFrameAdapterBasics:
    """Basic functionality tests for DataFrameAdapter."""

    def test_dataframe_to_models_many_true(self):
        """Test converting DataFrame to multiple model instances."""
        df = pd.DataFrame(
            [{"id": 1, "name": "Alice", "value": 10.5}, {"id": 2, "name": "Bob", "value": 20.3}]
        )

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "Alice"
        assert result[0].value == 10.5
        assert result[1].id == 2
        assert result[1].name == "Bob"
        assert result[1].value == 20.3

    def test_dataframe_to_models_many_false(self):
        """Test converting DataFrame to single model instance (first row)."""
        df = pd.DataFrame(
            [{"id": 1, "name": "Alice", "value": 10.5}, {"id": 2, "name": "Bob", "value": 20.3}]
        )

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=False)

        assert isinstance(result, SimpleModel)
        assert result.id == 1
        assert result.name == "Alice"
        assert result.value == 10.5

    def test_models_to_dataframe_many_true(self):
        """Test converting multiple model instances to DataFrame."""
        models = [
            SimpleModel(id=1, name="Alice", value=10.5),
            SimpleModel(id=2, name="Bob", value=20.3),
        ]

        result = DataFrameAdapter.to_obj(models, many=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["id", "name", "value"]
        assert result.iloc[0]["id"] == 1
        assert result.iloc[0]["name"] == "Alice"
        assert result.iloc[0]["value"] == 10.5
        assert result.iloc[1]["id"] == 2

    def test_models_to_dataframe_single_instance(self):
        """Test converting single model instance to DataFrame (creates 1-row DataFrame)."""
        model = SimpleModel(id=1, name="Alice", value=10.5)

        result = DataFrameAdapter.to_obj(model, many=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["id"] == 1
        assert result.iloc[0]["name"] == "Alice"

    def test_dataframe_roundtrip(self):
        """Test full roundtrip: models -> DataFrame -> models."""
        original_models = [
            SimpleModel(id=1, name="Alice", value=10.5),
            SimpleModel(id=2, name="Bob", value=20.3),
        ]

        # Convert to DataFrame
        df = DataFrameAdapter.to_obj(original_models, many=True)

        # Convert back to models
        result_models = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert len(result_models) == len(original_models)
        for original, result in zip(original_models, result_models, strict=False):
            assert original.id == result.id
            assert original.name == result.name
            assert original.value == result.value


class TestDataFrameAdapterErrorHandling:
    """Error handling tests for DataFrameAdapter."""

    def test_empty_dataframe_many_true(self):
        """Test empty DataFrame with many=True returns empty list."""
        df = pd.DataFrame(columns=["id", "name", "value"])

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_empty_dataframe_many_false(self):
        """Test empty DataFrame with many=False raises ResourceError."""
        df = pd.DataFrame(columns=["id", "name", "value"])

        with pytest.raises(ResourceError) as exc_info:
            DataFrameAdapter.from_obj(SimpleModel, df, many=False)

        assert "empty dataframe" in str(exc_info.value).lower()
        assert "many=false" in str(exc_info.value).lower()

    def test_validation_error_invalid_type(self):
        """Test validation error when DataFrame has invalid data types."""
        df = pd.DataFrame([{"id": "not_an_int", "name": "Alice", "value": 10.5}])

        with pytest.raises(AdapterValidationError) as exc_info:
            DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert "validation" in str(exc_info.value).lower()

    def test_validation_error_missing_field(self):
        """Test validation error when DataFrame is missing required fields."""
        df = pd.DataFrame([{"id": 1, "name": "Alice"}])  # Missing 'value'

        with pytest.raises(AdapterValidationError):
            DataFrameAdapter.from_obj(SimpleModel, df, many=True)

    def test_required_columns_validation_pass(self):
        """Test required_columns parameter allows valid DataFrame."""
        df = pd.DataFrame([{"id": 1, "name": "Alice", "value": 10.5, "extra": "ignored"}])

        result = DataFrameAdapter.from_obj(
            SimpleModel, df, many=True, required_columns=["id", "name", "value"]
        )

        assert len(result) == 1
        assert result[0].id == 1

    def test_required_columns_validation_fail(self):
        """Test required_columns parameter rejects DataFrame with missing columns."""
        df = pd.DataFrame([{"id": 1, "name": "Alice"}])  # Missing 'value'

        with pytest.raises(AdapterValidationError) as exc_info:
            DataFrameAdapter.from_obj(
                SimpleModel, df, many=True, required_columns=["id", "name", "value"]
            )

        assert "missing required columns" in str(exc_info.value).lower()
        assert "value" in str(exc_info.value)


class TestDataFrameAdapterEdgeCases:
    """Edge case tests for DataFrameAdapter."""

    def test_mixed_types_handling(self):
        """Test DataFrame with mixed types (int, float, str, bool, datetime)."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Alice",
                    "value": 10.5,
                    "is_active": True,
                    "created_at": now,
                    "optional_field": "test",
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "value": 20.3,
                    "is_active": False,
                    "created_at": now,
                    "optional_field": None,
                },
            ]
        )

        result = DataFrameAdapter.from_obj(ComplexModel, df, many=True)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].is_active is True
        assert result[0].created_at == now
        assert result[0].optional_field == "test"
        assert result[1].optional_field is None

    def test_null_handling_with_optional_fields(self):
        """Test handling of None/NaN values with Optional fields."""
        df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "name": "Alice",
                    "value": 10.5,
                    "is_active": True,
                    "created_at": datetime.now(),
                    "optional_field": None,
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "value": 20.3,
                    "is_active": False,
                    "created_at": datetime.now(),
                    "optional_field": "value",
                },
            ]
        )

        result = DataFrameAdapter.from_obj(ComplexModel, df, many=True)

        assert result[0].optional_field is None
        assert result[1].optional_field == "value"

    def test_special_characters_in_strings(self):
        """Test handling of special characters in string fields."""
        df = pd.DataFrame(
            [
                {"id": 1, "name": "O'Reilly", "value": 10.5},
                {"id": 2, "name": "Smith, Jr.", "value": 20.3},
                {"id": 3, "name": 'Test\n"Quotes"', "value": 30.1},
            ]
        )

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert len(result) == 3
        assert result[0].name == "O'Reilly"
        assert result[1].name == "Smith, Jr."
        assert result[2].name == 'Test\n"Quotes"'

    def test_large_dataset(self):
        """Test handling of large dataset (1000+ rows)."""
        data = [{"id": i, "name": f"Person_{i}", "value": float(i * 10.5)} for i in range(1000)]
        df = pd.DataFrame(data)

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert len(result) == 1000
        assert result[0].id == 0
        assert result[999].id == 999
        assert result[999].name == "Person_999"

    def test_dataframe_with_index(self):
        """Test DataFrame with custom index is handled correctly."""
        df = pd.DataFrame(
            [{"id": 1, "name": "Alice", "value": 10.5}, {"id": 2, "name": "Bob", "value": 20.3}]
        )
        df.index = ["row1", "row2"]

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2

    def test_extra_columns_ignored(self):
        """Test that extra columns in DataFrame are ignored during conversion."""
        df = pd.DataFrame(
            [
                {"id": 1, "name": "Alice", "value": 10.5, "extra1": "ignored", "extra2": 999},
                {"id": 2, "name": "Bob", "value": 20.3, "extra1": "also_ignored", "extra2": 888},
            ]
        )

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=True)

        assert len(result) == 2
        assert result[0].id == 1
        assert not hasattr(result[0], "extra1")
        assert not hasattr(result[0], "extra2")


# ===== SeriesAdapter Tests =====


class TestSeriesAdapterBasics:
    """Basic functionality tests for SeriesAdapter."""

    def test_series_to_model(self):
        """Test converting Series to single model instance."""
        series = pd.Series({"id": 1, "name": "Alice", "value": 10.5})

        result = SeriesAdapter.from_obj(SimpleModel, series)

        assert isinstance(result, SimpleModel)
        assert result.id == 1
        assert result.name == "Alice"
        assert result.value == 10.5

    def test_model_to_series(self):
        """Test converting single model instance to Series."""
        model = SimpleModel(id=1, name="Alice", value=10.5)

        result = SeriesAdapter.to_obj(model)

        assert isinstance(result, pd.Series)
        assert result["id"] == 1
        assert result["name"] == "Alice"
        assert result["value"] == 10.5

    def test_series_roundtrip(self):
        """Test full roundtrip: model -> Series -> model."""
        original = SimpleModel(id=1, name="Alice", value=10.5)

        # Convert to Series
        series = SeriesAdapter.to_obj(original)

        # Convert back to model
        result = SeriesAdapter.from_obj(SimpleModel, series)

        assert result.id == original.id
        assert result.name == original.name
        assert result.value == original.value


class TestSeriesAdapterErrorHandling:
    """Error handling tests for SeriesAdapter."""

    def test_series_from_obj_many_true_raises(self):
        """Test SeriesAdapter raises error when many=True is specified."""
        series = pd.Series({"id": 1, "name": "Alice", "value": 10.5})

        with pytest.raises(AdapterValidationError) as exc_info:
            SeriesAdapter.from_obj(SimpleModel, series, many=True)

        assert "single records only" in str(exc_info.value).lower()
        assert "many=False" in str(exc_info.value)

    def test_series_to_obj_many_true_raises(self):
        """Test SeriesAdapter raises error when many=True is specified for to_obj."""
        model = SimpleModel(id=1, name="Alice", value=10.5)

        with pytest.raises(AdapterValidationError) as exc_info:
            SeriesAdapter.to_obj(model, many=True)

        assert "single records only" in str(exc_info.value).lower()

    def test_series_to_obj_list_raises(self):
        """Test SeriesAdapter raises error when list of models is provided."""
        models = [
            SimpleModel(id=1, name="Alice", value=10.5),
            SimpleModel(id=2, name="Bob", value=20.3),
        ]

        with pytest.raises(AdapterValidationError) as exc_info:
            SeriesAdapter.to_obj(models)

        assert "single records only" in str(exc_info.value).lower()

    def test_series_validation_error(self):
        """Test validation error when Series has invalid data."""
        series = pd.Series({"id": "not_an_int", "name": "Alice", "value": 10.5})

        with pytest.raises(AdapterValidationError):
            SeriesAdapter.from_obj(SimpleModel, series)

    def test_series_missing_field(self):
        """Test validation error when Series is missing required field."""
        series = pd.Series({"id": 1, "name": "Alice"})  # Missing 'value'

        with pytest.raises(AdapterValidationError):
            SeriesAdapter.from_obj(SimpleModel, series)


class TestSeriesAdapterEdgeCases:
    """Edge case tests for SeriesAdapter."""

    def test_series_mixed_types(self):
        """Test Series with mixed types."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        series = pd.Series(
            {
                "id": 1,
                "name": "Alice",
                "value": 10.5,
                "is_active": True,
                "created_at": now,
                "optional_field": "test",
            }
        )

        result = SeriesAdapter.from_obj(ComplexModel, series)

        assert result.id == 1
        assert result.name == "Alice"
        assert result.value == 10.5
        assert result.is_active is True
        assert result.created_at == now
        assert result.optional_field == "test"

    def test_series_with_none_values(self):
        """Test Series with None values in Optional fields."""
        series = pd.Series(
            {
                "id": 1,
                "name": "Alice",
                "value": 10.5,
                "is_active": True,
                "created_at": datetime.now(),
                "optional_field": None,
            }
        )

        result = SeriesAdapter.from_obj(ComplexModel, series)

        assert result.optional_field is None

    def test_series_special_characters(self):
        """Test Series with special characters in strings."""
        series = pd.Series({"id": 1, "name": 'O\'Reilly "Test"', "value": 10.5})

        result = SeriesAdapter.from_obj(SimpleModel, series)

        assert result.name == 'O\'Reilly "Test"'

    def test_series_extra_fields_ignored(self):
        """Test that extra fields in Series are ignored."""
        series = pd.Series(
            {"id": 1, "name": "Alice", "value": 10.5, "extra1": "ignored", "extra2": 999}
        )

        result = SeriesAdapter.from_obj(SimpleModel, series)

        assert result.id == 1
        assert result.name == "Alice"
        assert not hasattr(result, "extra1")


# ===== Advanced Tests =====


class TestDataFrameAdapterAdvanced:
    """Advanced tests for DataFrameAdapter."""

    def test_custom_adapt_method(self):
        """Test using custom adapt_meth for conversion."""

        class CustomModel(BaseModel):
            id: int
            name: str

            @classmethod
            def custom_validate(cls, data):
                # Custom validation logic
                if isinstance(data, dict):
                    data["name"] = data["name"].upper()
                return cls(**data)

        df = pd.DataFrame([{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}])

        result = DataFrameAdapter.from_obj(CustomModel, df, many=True, adapt_meth="custom_validate")

        assert result[0].name == "ALICE"
        assert result[1].name == "BOB"

    def test_adapt_kw_parameters(self):
        """Test passing adapt_kw parameters to model validation."""

        class FlexibleModel(BaseModel):
            id: int
            name: str
            value: float

            model_config = {"extra": "forbid"}

        df = pd.DataFrame([{"id": 1, "name": "Alice", "value": 10.5}])

        # Should work with default settings
        result = DataFrameAdapter.from_obj(FlexibleModel, df, many=True)
        assert len(result) == 1

    def test_dataframe_column_order_preserved(self):
        """Test that column order is preserved in DataFrame output."""
        models = [
            SimpleModel(id=1, name="Alice", value=10.5),
            SimpleModel(id=2, name="Bob", value=20.3),
        ]

        result = DataFrameAdapter.to_obj(models, many=True)

        # Column order should match model field order
        assert list(result.columns) == ["id", "name", "value"]

    def test_dataframe_empty_list_to_dataframe(self):
        """Test converting empty list to DataFrame."""
        models = []

        result = DataFrameAdapter.to_obj(models, many=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestErrorHandlingEdgeCases:
    """Tests for edge cases in error handling paths."""

    def test_dataframe_model_dump_failure(self):
        """Test handling of model_dump failures."""

        class BrokenModel(BaseModel):
            id: int
            name: str

            def model_dump(self, **kwargs):
                raise RuntimeError("Simulated dump failure")

        model = BrokenModel(id=1, name="test")

        with pytest.raises(AdapterValidationError):
            DataFrameAdapter.to_obj([model], many=True)

    def test_series_model_dump_failure(self):
        """Test handling of model_dump failures in SeriesAdapter."""

        class BrokenModel(BaseModel):
            id: int
            name: str

            def model_dump(self, **kwargs):
                raise RuntimeError("Simulated dump failure")

        model = BrokenModel(id=1, name="test")

        with pytest.raises(AdapterValidationError):
            SeriesAdapter.to_obj(model)

    def test_dataframe_custom_validation_errors(self):
        """Test custom validation error types."""

        class CustomValidationError(Exception):
            def errors(self):
                return [{"loc": ["field"], "msg": "error"}]

        class CustomModel(BaseModel):
            id: int
            name: str

            @classmethod
            def model_validate(cls, data):
                raise CustomValidationError("Custom error")

        df = pd.DataFrame([{"id": 1, "name": "test"}])

        with pytest.raises(AdapterValidationError):
            DataFrameAdapter.from_obj(
                CustomModel, df, many=True, validation_errors=(CustomValidationError,)
            )

    def test_dataframe_from_single_with_validation_context(self):
        """Test DataFrame single row conversion with validation context."""
        df = pd.DataFrame([{"id": 1, "name": "  Alice  ", "value": 10.5}])

        result = DataFrameAdapter.from_obj(SimpleModel, df, many=False)

        assert result.id == 1
        assert result.name == "  Alice  "

    def test_series_to_dict_with_kwargs(self):
        """Test Series to_dict with additional kwargs."""
        series = pd.Series({"id": 1, "name": "Alice", "value": 10.5})

        # This tests the **kw parameter in from_obj
        result = SeriesAdapter.from_obj(SimpleModel, series, into=dict)

        assert result.id == 1
        assert result.name == "Alice"

    def test_dataframe_validation_with_multiple_rows_error(self):
        """Test validation error on second row of many rows."""
        df = pd.DataFrame(
            [
                {"id": 1, "name": "Alice", "value": 10.5},
                {"id": "invalid", "name": "Bob", "value": 20.3},  # Invalid on second row
            ]
        )

        with pytest.raises(AdapterValidationError):
            DataFrameAdapter.from_obj(SimpleModel, df, many=True)

    def test_dataframe_unexpected_error_in_validation(self):
        """Test handling of truly unexpected errors during validation."""
        from unittest.mock import patch

        df = pd.DataFrame([{"id": 1, "name": "Alice", "value": 10.5}])

        # Patch to_dict to raise an unexpected error
        with patch.object(
            pd.DataFrame, "to_dict", side_effect=RuntimeError("Unexpected pandas error")
        ):
            with pytest.raises(AdapterValidationError):
                DataFrameAdapter.from_obj(SimpleModel, df, many=True)

    def test_series_unexpected_error_in_to_dict(self):
        """Test handling of unexpected errors in Series to_dict."""
        from unittest.mock import patch

        series = pd.Series({"id": 1, "name": "Alice", "value": 10.5})

        # Patch to_dict to raise an unexpected error
        with patch.object(
            pd.Series, "to_dict", side_effect=RuntimeError("Unexpected series error")
        ):
            with pytest.raises(AdapterValidationError):
                SeriesAdapter.from_obj(SimpleModel, series)
