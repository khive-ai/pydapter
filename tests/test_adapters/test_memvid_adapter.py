"""
Tests for Memvid adapter functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from pydapter.core import Adaptable
from pydapter.exceptions import (
    ConnectionError,
    QueryError,
    ResourceError,
    ValidationError,
)
from pydapter.extras.memvid_ import MemvidAdapter


@pytest.fixture
def memvid_model_factory():
    """Factory for creating test models with Memvid adapter registered."""

    def create_model(**kw):
        class TestDocument(Adaptable, BaseModel):
            id: str
            text: str
            category: str = "general"

        # Register the Memvid adapter
        TestDocument.register_adapter(MemvidAdapter)
        return TestDocument(**kw)

    return create_model


@pytest.fixture
def memvid_sample(memvid_model_factory):
    """Create a sample document instance."""
    return memvid_model_factory(
        id="doc1",
        text="This is sample content for testing memvid adapter functionality.",
        category="test",
    )


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_file = Path(tmpdir) / "test_memory.mp4"
        index_file = Path(tmpdir) / "test_index.json"
        yield str(video_file), str(index_file)


class TestMemvidAdapterProtocol:
    """Tests for Memvid adapter protocol compliance."""

    def test_memvid_adapter_protocol_compliance(self):
        """Test that MemvidAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(MemvidAdapter, "obj_key")
        assert isinstance(MemvidAdapter.obj_key, str)
        assert MemvidAdapter.obj_key == "memvid"

        # Verify method signatures
        assert hasattr(MemvidAdapter, "from_obj")
        assert hasattr(MemvidAdapter, "to_obj")


class TestMemvidAdapterImport:
    """Tests for Memvid import handling."""

    def test_import_memvid_success(self):
        """Test successful memvid import."""
        with (
            patch("memvid.MemvidEncoder"),
            patch("memvid.MemvidRetriever"),
        ):
            encoder_cls, retriever_cls = MemvidAdapter._import_memvid()
            assert encoder_cls is not None
            assert retriever_cls is not None

    def test_import_memvid_failure(self):
        """Test memvid import failure."""
        with patch("builtins.__import__", side_effect=ImportError("memvid not found")):
            with pytest.raises(ConnectionError) as exc_info:
                MemvidAdapter._import_memvid()

            assert "Failed to import memvid" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"


class TestMemvidAdapterToObj:
    """Tests for MemvidAdapter.to_obj (encoding to video memory)."""

    def test_to_obj_validation_errors(self):
        """Test validation errors for required parameters."""
        sample = Mock()

        # Missing video_file
        with pytest.raises(TypeError) as exc_info:
            MemvidAdapter.to_obj(sample, index_file="test.json")
        assert "video_file" in str(exc_info.value)

        # Missing index_file
        with pytest.raises(TypeError) as exc_info:
            MemvidAdapter.to_obj(sample, video_file="test.mp4")
        assert "index_file" in str(exc_info.value)

    def test_to_obj_empty_string_parameters(self, temp_files):
        """Test validation with empty string parameters."""
        video_file, index_file = temp_files
        sample = Mock()

        # Empty video_file
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.to_obj(sample, video_file="", index_file=index_file)
        assert "Missing required parameter 'video_file'" in str(exc_info.value)

        # Empty index_file
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.to_obj(sample, video_file=video_file, index_file="")
        assert "Missing required parameter 'index_file'" in str(exc_info.value)

    def test_to_obj_empty_data(self, temp_files):
        """Test handling empty data."""
        video_file, index_file = temp_files

        result = MemvidAdapter.to_obj([], video_file=video_file, index_file=index_file)

        assert result == {"encoded_count": 0}

    def test_to_obj_missing_text_field(self, temp_files):
        """Test error when text field is missing."""
        video_file, index_file = temp_files

        # Create mock object without text field
        mock_obj = Mock()
        mock_obj.model_dump.return_value = {"id": "1", "name": "test"}

        # Make hasattr return False for the text field
        with patch("builtins.hasattr", return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                MemvidAdapter.to_obj(
                    mock_obj, video_file=video_file, index_file=index_file
                )

            assert "Text field 'text' not found in model" in str(exc_info.value)

    def test_to_obj_success(self, memvid_sample, temp_files):
        """Test successful video memory creation."""
        video_file, index_file = temp_files

        # Mock the import method to return mock classes
        mock_encoder = Mock()
        mock_encoder.build_video.return_value = {"chunks": 3, "frames": 100}
        mock_encoder_class = Mock(return_value=mock_encoder)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(mock_encoder_class, Mock())
        ):
            result = MemvidAdapter.to_obj(
                memvid_sample,
                video_file=video_file,
                index_file=index_file,
                chunk_size=512,
                overlap=25,
            )

            # Verify encoder was created and used correctly
            mock_encoder_class.assert_called_once()
            mock_encoder.add_text.assert_called_once_with(
                memvid_sample.text, chunk_size=512, overlap=25
            )
            mock_encoder.build_video.assert_called_once_with(
                video_file,
                index_file,
                codec="h265",
                show_progress=False,
                allow_fallback=True,
            )

            # Verify result
            assert result["encoded_count"] == 1
            assert result["video_file"] == video_file
            assert result["index_file"] == index_file
            assert result["chunks"] == 3
            assert result["frames"] == 100

    def test_to_obj_encoder_creation_failure(self, memvid_sample, temp_files):
        """Test MemvidEncoder creation failure."""
        video_file, index_file = temp_files

        # Mock the import method to return a mock class that raises on instantiation
        mock_encoder_class = Mock(side_effect=RuntimeError("Encoder creation failed"))

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(mock_encoder_class, Mock())
        ):
            with pytest.raises(ConnectionError) as exc_info:
                MemvidAdapter.to_obj(
                    memvid_sample, video_file=video_file, index_file=index_file
                )

            assert "Failed to create MemvidEncoder" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_to_obj_non_string_text_field(self, temp_files):
        """Test error when text field is not a string."""
        video_file, index_file = temp_files

        # Create mock object with non-string text field
        mock_obj = Mock()
        mock_obj.text = 123  # Non-string value
        mock_obj.model_dump.return_value = {"id": "1", "text": 123}

        # Mock the import method to return mock classes
        mock_encoder = Mock()
        mock_encoder_class = Mock(return_value=mock_encoder)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(mock_encoder_class, Mock())
        ):
            with pytest.raises(ValidationError) as exc_info:
                MemvidAdapter.to_obj(
                    mock_obj, video_file=video_file, index_file=index_file
                )

            assert "Text field 'text' must be a string" in str(exc_info.value)

    def test_to_obj_text_processing_error(self, temp_files):
        """Test error during text processing."""
        video_file, index_file = temp_files

        # Create mock object
        mock_obj = Mock()
        mock_obj.text = "valid text"
        mock_obj.model_dump.return_value = {"id": "1", "text": "valid text"}

        # Mock encoder that fails during add_text
        mock_encoder = Mock()
        mock_encoder.add_text.side_effect = RuntimeError("Text processing failed")
        mock_encoder_class = Mock(return_value=mock_encoder)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(mock_encoder_class, Mock())
        ):
            with pytest.raises(QueryError) as exc_info:
                MemvidAdapter.to_obj(
                    mock_obj, video_file=video_file, index_file=index_file
                )

            assert "Error processing text chunks" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_to_obj_build_video_failure(self, memvid_sample, temp_files):
        """Test build video failure."""
        video_file, index_file = temp_files

        # Mock encoder that fails during build_video
        mock_encoder = Mock()
        mock_encoder.add_text.return_value = None
        mock_encoder.build_video.side_effect = RuntimeError("Build video failed")
        mock_encoder_class = Mock(return_value=mock_encoder)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(mock_encoder_class, Mock())
        ):
            with pytest.raises(QueryError) as exc_info:
                MemvidAdapter.to_obj(
                    memvid_sample, video_file=video_file, index_file=index_file
                )

            assert "Failed to build video memory" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_to_obj_unexpected_error(self, temp_files):
        """Test unexpected error handling."""
        video_file, index_file = temp_files

        # Create mock that raises unexpected error type
        mock_obj = Mock()
        mock_obj.text = "valid text"
        mock_obj.model_dump.side_effect = TypeError("Unexpected error")

        with patch.object(MemvidAdapter, "_import_memvid"):
            with pytest.raises(QueryError) as exc_info:
                MemvidAdapter.to_obj(
                    mock_obj, video_file=video_file, index_file=index_file
                )

            assert "Unexpected error in Memvid adapter" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"


class TestMemvidAdapterFromObj:
    """Tests for MemvidAdapter.from_obj (searching video memory)."""

    def test_from_obj_validation_errors(self):
        """Test validation errors for required parameters."""

        # Missing video_file
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(Mock, {"index_file": "test.json", "query": "test"})
        assert "video_file" in str(exc_info.value)

        # Missing index_file
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(Mock, {"video_file": "test.mp4", "query": "test"})
        assert "index_file" in str(exc_info.value)

        # Missing query
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(
                Mock, {"video_file": "test.mp4", "index_file": "test.json"}
            )
        assert "query" in str(exc_info.value)

    def test_from_obj_file_not_found(self):
        """Test error when video memory files are not found."""
        mock_retriever_class = Mock(
            side_effect=FileNotFoundError("Video file not found")
        )

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with pytest.raises(ResourceError) as exc_info:
                MemvidAdapter.from_obj(
                    Mock,
                    {
                        "video_file": "nonexistent.mp4",
                        "index_file": "nonexistent.json",
                        "query": "test",
                    },
                )

            assert "Video memory files not found" in str(exc_info.value)

    def test_from_obj_no_results(self):
        """Test handling when no search results are found."""
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.return_value = []
        mock_retriever_class = Mock(return_value=mock_retriever)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            # Test many=True returns empty list
            result = MemvidAdapter.from_obj(
                Mock,
                {
                    "video_file": "test.mp4",
                    "index_file": "test.json",
                    "query": "nonexistent query",
                },
                many=True,
            )
            assert result == []

            # Test many=False raises ResourceError
            with pytest.raises(ResourceError) as exc_info:
                MemvidAdapter.from_obj(
                    Mock,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "nonexistent query",
                    },
                    many=False,
                )
            assert "No results found for query" in str(exc_info.value)

    def test_from_obj_retriever_creation_failure(self):
        """Test MemvidRetriever creation failure."""
        mock_retriever_class = Mock(
            side_effect=RuntimeError("Retriever creation failed")
        )

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with pytest.raises(ConnectionError) as exc_info:
                MemvidAdapter.from_obj(
                    Mock,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "test",
                    },
                )

            assert "Failed to create MemvidRetriever" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_from_obj_search_execution_failure(self):
        """Test search execution failure."""
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.side_effect = RuntimeError("Search failed")
        mock_retriever_class = Mock(return_value=mock_retriever)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with pytest.raises(QueryError) as exc_info:
                MemvidAdapter.from_obj(
                    Mock,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "test query",
                    },
                )

            assert "Error searching video memory" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_from_obj_single_result_success(self):
        """Test successful single result return."""
        # Mock retriever results
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.return_value = [
            {"text": "Sample content", "score": 0.95}
        ]
        mock_retriever_class = Mock(return_value=mock_retriever)

        # Create model class for validation
        class TestDoc(Adaptable, BaseModel):
            id: str
            text: str

        TestDoc.register_adapter(MemvidAdapter)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with patch.object(TestDoc, "model_validate") as mock_validate:
                mock_validate.return_value = Mock(id="0", text="Sample content")

                result = MemvidAdapter.from_obj(
                    TestDoc,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "testing content",
                    },
                    many=False,
                )

                # Verify single result returned
                assert result is not None
                mock_validate.assert_called_once()

    def test_from_obj_validation_fallback(self):
        """Test fallback validation when primary validation fails."""
        # Mock retriever results
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.return_value = [
            {"text": "Sample content", "score": 0.95}
        ]
        mock_retriever_class = Mock(return_value=mock_retriever)

        # Create model class that requires specific fields
        class StrictTestDoc(Adaptable, BaseModel):
            id: str
            text: str
            required_field: str  # This will cause first validation to fail

        StrictTestDoc.register_adapter(MemvidAdapter)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with patch.object(StrictTestDoc, "model_validate") as mock_validate:
                # First call fails, second call succeeds
                mock_validate.side_effect = [
                    PydanticValidationError.from_exception_data(
                        "StrictTestDoc",
                        [
                            {
                                "type": "missing",
                                "loc": ("required_field",),
                                "msg": "Field required",
                            }
                        ],
                    ),
                    Mock(id="0", text="Sample content"),
                ]

                result = MemvidAdapter.from_obj(
                    StrictTestDoc,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "testing content",
                    },
                    many=True,
                )

                # Verify fallback worked
                assert len(result) == 1
                assert mock_validate.call_count == 2

    def test_from_obj_validation_error(self):
        """Test validation error during result conversion."""
        # Mock retriever results
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.return_value = [
            {"text": "Sample content", "score": 0.95}
        ]
        mock_retriever_class = Mock(return_value=mock_retriever)

        # Create model class
        class TestDoc(Adaptable, BaseModel):
            id: str
            text: str

        TestDoc.register_adapter(MemvidAdapter)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with patch.object(TestDoc, "model_validate") as mock_validate:
                # Both validation attempts fail
                validation_error = PydanticValidationError.from_exception_data(
                    "TestDoc",
                    [{"type": "missing", "loc": ("id",), "msg": "Field required"}],
                )
                mock_validate.side_effect = [validation_error, validation_error]

                with pytest.raises(ValidationError) as exc_info:
                    MemvidAdapter.from_obj(
                        TestDoc,
                        {
                            "video_file": "test.mp4",
                            "index_file": "test.json",
                            "query": "testing content",
                        },
                        many=True,
                    )

                assert "Validation error converting search results" in str(
                    exc_info.value
                )

    def test_from_obj_unexpected_error(self):
        """Test unexpected error handling in from_obj."""
        # Create mock that raises unexpected error
        with patch.object(
            MemvidAdapter, "_import_memvid", side_effect=TypeError("Unexpected error")
        ):
            with pytest.raises(QueryError) as exc_info:
                MemvidAdapter.from_obj(
                    Mock,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "test",
                    },
                )

            assert "Unexpected error in Memvid adapter" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_from_obj_success(self):
        """Test successful video memory search."""
        # Mock retriever results
        mock_retriever = Mock()
        mock_retriever.search_with_metadata.return_value = [
            {"text": "Sample content about testing", "score": 0.95},
            {"text": "Another relevant piece of text", "score": 0.87},
        ]
        mock_retriever_class = Mock(return_value=mock_retriever)

        # Create model class for validation
        class TestDoc(Adaptable, BaseModel):
            id: str
            text: str
            category: str = "general"

        TestDoc.register_adapter(MemvidAdapter)

        with patch.object(
            MemvidAdapter, "_import_memvid", return_value=(Mock(), mock_retriever_class)
        ):
            with patch.object(TestDoc, "model_validate") as mock_validate:
                # Mock successful validation
                mock_validate.side_effect = [
                    Mock(id="0", text="Sample content about testing"),
                    Mock(id="1", text="Another relevant piece of text"),
                ]

                result = MemvidAdapter.from_obj(
                    TestDoc,
                    {
                        "video_file": "test.mp4",
                        "index_file": "test.json",
                        "query": "testing content",
                        "top_k": 2,
                    },
                    many=True,
                )

                # Verify retriever was used correctly
                mock_retriever_class.assert_called_once_with("test.mp4", "test.json")
                mock_retriever.search_with_metadata.assert_called_once_with(
                    "testing content", top_k=2
                )

                # Verify results
                assert len(result) == 2
                assert mock_validate.call_count == 2


class TestMemvidAdapterIntegration:
    """Integration tests for Memvid adapter (require memvid to be installed)."""

    def test_adapter_registration(self, memvid_model_factory):
        """Test that Memvid adapter can be registered with models."""
        doc = memvid_model_factory(id="test", text="Sample text")

        # Verify adapter is registered
        # Check that the adapter is registered by checking the registry
        registry = doc.__class__._registry()
        adapter_keys = list(registry._reg.keys())
        assert "memvid" in adapter_keys
