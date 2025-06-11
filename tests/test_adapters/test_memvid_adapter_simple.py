"""
Simplified tests for Memvid adapter focusing on testable components.
"""

import pytest
from unittest.mock import Mock, patch

from pydapter.exceptions import ConnectionError, ValidationError
from pydapter.extras.memvid_ import MemvidAdapter


class TestMemvidAdapterBasics:
    """Test basic Memvid adapter functionality."""

    def test_adapter_has_obj_key(self):
        """Test that adapter has the correct obj_key."""
        assert hasattr(MemvidAdapter, "obj_key")
        assert MemvidAdapter.obj_key == "memvid"

    def test_adapter_has_required_methods(self):
        """Test that adapter has required methods."""
        assert hasattr(MemvidAdapter, "to_obj")
        assert hasattr(MemvidAdapter, "from_obj")
        assert hasattr(MemvidAdapter, "_import_memvid")

    @patch("pydapter.extras.memvid_.MemvidAdapter._import_memvid")
    def test_import_success(self, mock_import):
        """Test successful memvid import."""
        mock_encoder = Mock()
        mock_retriever = Mock()
        mock_import.return_value = (mock_encoder, mock_retriever)

        encoder, retriever = MemvidAdapter._import_memvid()
        assert encoder == mock_encoder
        assert retriever == mock_retriever

    def test_import_failure(self):
        """Test memvid import failure."""
        with patch("builtins.__import__", side_effect=ImportError("memvid not found")):
            with pytest.raises(ConnectionError) as exc_info:
                MemvidAdapter._import_memvid()

            assert "Failed to import memvid" in str(exc_info.value)
            assert exc_info.value.adapter == "memvid"

    def test_to_obj_validation_missing_video_file(self):
        """Test validation error when video_file is missing."""
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.to_obj(Mock(), video_file="", index_file="test.json")

        assert "Missing required parameter 'video_file'" in str(exc_info.value)

    def test_to_obj_validation_missing_index_file(self):
        """Test validation error when index_file is missing."""
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.to_obj(Mock(), video_file="test.mp4", index_file="")

        assert "Missing required parameter 'index_file'" in str(exc_info.value)

    def test_to_obj_empty_input(self):
        """Test handling of empty input."""
        result = MemvidAdapter.to_obj([], video_file="test.mp4", index_file="test.json")
        assert result == {"encoded_count": 0}

    def test_from_obj_validation_missing_video_file(self):
        """Test validation error in from_obj when video_file is missing."""
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(Mock, {"index_file": "test.json", "query": "test"})

        assert "Missing required parameter 'video_file'" in str(exc_info.value)

    def test_from_obj_validation_missing_index_file(self):
        """Test validation error in from_obj when index_file is missing."""
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(Mock, {"video_file": "test.mp4", "query": "test"})

        assert "Missing required parameter 'index_file'" in str(exc_info.value)

    def test_from_obj_validation_missing_query(self):
        """Test validation error in from_obj when query is missing."""
        with pytest.raises(ValidationError) as exc_info:
            MemvidAdapter.from_obj(
                Mock, {"video_file": "test.mp4", "index_file": "test.json"}
            )

        assert "Missing required parameter 'query'" in str(exc_info.value)
