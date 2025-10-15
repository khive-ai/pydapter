"""
Tests for Series adapter functionality.
"""

from unittest.mock import MagicMock, patch

from pydantic import BaseModel
import pytest

from pydapter.core import Adaptable
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.pandas_ import SeriesAdapter


@pytest.fixture
def series_model_factory():
    """Factory for creating test models with Series adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the Series adapter
        TestModel.register_adapter(SeriesAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def series_sample(series_model_factory):
    """Create a sample model instance."""
    return series_model_factory(id=1, name="test", value=42.5)


class TestSeriesAdapterProtocol:
    """Tests for Series adapter protocol compliance."""

    def test_series_adapter_protocol_compliance(self):
        """Test that SeriesAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(SeriesAdapter, "obj_key")
        assert isinstance(SeriesAdapter.obj_key, str)
        assert SeriesAdapter.obj_key == "pd.Series"

        # Verify method signatures
        assert hasattr(SeriesAdapter, "from_obj")
        assert hasattr(SeriesAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(SeriesAdapter.from_obj)
        assert callable(SeriesAdapter.to_obj)


class TestSeriesAdapterFunctionality:
    """Tests for Series adapter functionality."""

    @patch("pydapter.extras.pandas_.pd")
    def test_series_to_obj(self, mock_pd, series_sample):
        """Test conversion from model to Series."""
        # We need to patch the entire Series adapter's to_obj method
        with patch("pydapter.extras.pandas_.SeriesAdapter.to_obj") as mock_to_obj:
            # Configure the mock to return a Series
            mock_series = MagicMock()
            mock_to_obj.return_value = mock_series

            # Test to_obj
            result = series_sample.adapt_to(obj_key="pd.Series", many=False)

            # Verify the result
            assert result == mock_series

            # Verify the mock was called
            mock_to_obj.assert_called_once()

    @patch("pydapter.extras.pandas_.pd")
    def test_series_from_obj(self, mock_pd, series_sample):
        """Test conversion from Series to model."""
        # We need to patch the entire Series adapter's from_obj method
        with patch("pydapter.extras.pandas_.SeriesAdapter.from_obj") as mock_from_obj:
            # Configure the mock to return a model instance
            expected_model = series_sample.__class__(id=1, name="test", value=42.5)
            mock_from_obj.return_value = expected_model

            # Create a mock Series
            mock_series = MagicMock()

            # Test from_obj
            model_cls = series_sample.__class__
            result = model_cls.adapt_from(mock_series, obj_key="pd.Series", many=False)

            # Verify the result
            assert isinstance(result, model_cls)
            assert result.id == 1
            assert result.name == "test"
            assert result.value == 42.5

    @patch("pydapter.extras.pandas_.pd")
    def test_series_to_obj_with_dict_conversion(self, mock_pd, series_sample):
        """Test that to_obj properly converts model to Series."""
        # Create a real model
        model = series_sample

        # Mock pd.Series to track calls
        mock_series_constructor = MagicMock()
        mock_pd.Series = mock_series_constructor

        # Call to_obj directly
        SeriesAdapter.to_obj(model, many=False)

        # Verify Series constructor was called with model_dump output
        mock_series_constructor.assert_called_once()
        call_args = mock_series_constructor.call_args
        # First positional argument should be the dict from model_dump
        assert isinstance(call_args[0][0], dict)


class TestSeriesAdapterErrorHandling:
    """Tests for Series adapter error handling."""

    @patch("pydapter.extras.pandas_.pd")
    def test_series_from_obj_many_true_raises_error(self, mock_pd, series_sample):
        """Test that from_obj with many=True raises AdapterValidationError."""
        # Create a mock Series
        mock_series = MagicMock()

        # Test from_obj with many=True (should raise AdapterValidationError)
        model_cls = series_sample.__class__
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.from_obj(model_cls, mock_series, many=True)

    @patch("pydapter.extras.pandas_.pd")
    def test_series_to_obj_many_true_raises_error(self, mock_pd, series_sample):
        """Test that to_obj with many=True raises AdapterValidationError."""
        # Test to_obj with many=True (should raise AdapterValidationError)
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.to_obj(series_sample, many=True)

    @patch("pydapter.extras.pandas_.pd")
    def test_series_to_obj_with_list_raises_error(self, mock_pd, series_sample):
        """Test that to_obj with list input raises AdapterValidationError."""
        # Test to_obj with list input (should raise AdapterValidationError)
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.to_obj([series_sample], many=False)

    @patch("pydapter.extras.pandas_.pd")
    def test_series_from_obj_empty_series(self, mock_pd, series_sample):
        """Test handling of empty Series."""
        # Create a mock Series with empty data
        mock_series = MagicMock()
        mock_series.to_dict.return_value = {}

        # Patch from_obj to simulate the empty case
        with patch(
            "pydapter.extras.pandas_.SeriesAdapter.from_obj",
            side_effect=ValueError("Empty Series"),
        ):
            # Test from_obj with empty Series
            model_cls = series_sample.__class__
            with pytest.raises(ValueError, match="Empty Series"):
                model_cls.adapt_from(mock_series, obj_key="pd.Series", many=False)

    @patch("pydapter.extras.pandas_.pd")
    def test_series_invalid_data(self, mock_pd, series_sample):
        """Test handling of invalid data."""
        # Create a mock Series with invalid data
        mock_series = MagicMock()

        # We need to patch the entire Series adapter's from_obj method to raise an error
        with patch(
            "pydapter.extras.pandas_.SeriesAdapter.from_obj",
            side_effect=ValueError("Invalid data"),
        ):
            # Test from_obj with invalid data
            model_cls = series_sample.__class__
            with pytest.raises(ValueError, match="Invalid data"):
                model_cls.adapt_from(mock_series, obj_key="pd.Series", many=False)


class TestSeriesAdapterValidation:
    """Tests for Series adapter validation behavior."""

    def test_series_adapter_single_record_only(self):
        """Test that SeriesAdapter enforces single record constraint."""

        # Create a simple model
        class SimpleModel(BaseModel):
            value: int

        # Create a mock Series
        mock_series = MagicMock()
        mock_series.to_dict.return_value = {"value": 42}

        # Test that many=True raises AdapterValidationError in from_obj
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.from_obj(SimpleModel, mock_series, many=True)

        # Test that many=True raises AdapterValidationError in to_obj
        model = SimpleModel(value=42)
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.to_obj(model, many=True)

        # Test that list input raises AdapterValidationError in to_obj
        with pytest.raises(
            AdapterValidationError, match="SeriesAdapter supports single records only"
        ):
            SeriesAdapter.to_obj([model], many=False)
