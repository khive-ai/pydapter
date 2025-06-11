"""
Simplified tests for Async Pulsar Memvid adapter focusing on testable components.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from pydapter.exceptions import ConnectionError, ValidationError
from pydapter.extras.async_memvid_pulsar import (
    AsyncPulsarMemvidAdapter,
    MemoryOperationResult,
    PulsarMemvidMessage,
)


class TestAsyncPulsarMemvidAdapterBasics:
    """Test basic AsyncPulsarMemvidAdapter functionality."""

    def test_adapter_has_obj_key(self):
        """Test that adapter has the correct obj_key."""
        assert hasattr(AsyncPulsarMemvidAdapter, "obj_key")
        assert AsyncPulsarMemvidAdapter.obj_key == "pulsar_memvid"

    def test_adapter_has_required_methods(self):
        """Test that adapter has required methods."""
        assert hasattr(AsyncPulsarMemvidAdapter, "to_obj")
        assert hasattr(AsyncPulsarMemvidAdapter, "from_obj")
        assert hasattr(AsyncPulsarMemvidAdapter, "_import_dependencies")

    @pytest.mark.asyncio
    async def test_import_dependencies_success(self):
        """Test successful dependency import."""

        def mock_import(name, *args, **kwargs):
            if name == "pulsar":
                return Mock()
            elif name == "memvid":
                mock_module = Mock()
                mock_module.MemvidEncoder = Mock()
                mock_module.MemvidRetriever = Mock()
                return mock_module
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            (
                pulsar,
                encoder,
                retriever,
            ) = await AsyncPulsarMemvidAdapter._import_dependencies()
            assert pulsar is not None
            assert encoder is not None
            assert retriever is not None

    @pytest.mark.asyncio
    async def test_import_dependencies_pulsar_missing(self):
        """Test error when Pulsar is missing."""

        def mock_import(name, *args, **kwargs):
            if name == "pulsar":
                raise ImportError("No module named 'pulsar'")
            elif name == "memvid":
                return Mock()
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ConnectionError) as exc_info:
                await AsyncPulsarMemvidAdapter._import_dependencies()

            assert "Failed to import pulsar-client" in str(exc_info.value)
            assert exc_info.value.adapter == "pulsar_memvid"

    @pytest.mark.asyncio
    async def test_import_dependencies_memvid_missing(self):
        """Test error when Memvid is missing."""

        def mock_import(name, *args, **kwargs):
            if name == "memvid":
                raise ImportError("No module named 'memvid'")
            elif name == "pulsar":
                return Mock()
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ConnectionError) as exc_info:
                await AsyncPulsarMemvidAdapter._import_dependencies()

            assert "Failed to import memvid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_validation_missing_pulsar_url(self):
        """Test validation error when pulsar_url is missing."""
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.to_obj(
                Mock(),
                pulsar_url="",
                topic="test",
                memory_id="mem1",
                video_file="test.mp4",
                index_file="test.json",
            )
        assert "Missing required parameter 'pulsar_url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_validation_missing_topic(self):
        """Test validation error when topic is missing."""
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.to_obj(
                Mock(),
                pulsar_url="pulsar://localhost:6650",
                topic="",
                memory_id="mem1",
                video_file="test.mp4",
                index_file="test.json",
            )
        assert "Missing required parameter 'topic'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_obj_empty_data(self):
        """Test handling empty data."""
        result = await AsyncPulsarMemvidAdapter.to_obj(
            [],
            pulsar_url="pulsar://localhost:6650",
            topic="test-topic",
            memory_id="test-memory",
            video_file="test.mp4",
            index_file="test.json",
        )

        assert result == {"message_count": 0, "memory_id": "test-memory"}

    @pytest.mark.asyncio
    async def test_from_obj_validation_missing_pulsar_url(self):
        """Test validation error when pulsar_url is missing."""
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.from_obj(
                Mock, {"search_topic": "test", "memory_id": "mem1"}
            )
        assert "Missing required parameter 'pulsar_url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with (
            patch.object(AsyncPulsarMemvidAdapter, "_import_dependencies"),
            patch.object(
                AsyncPulsarMemvidAdapter, "_create_pulsar_client"
            ) as mock_create,
        ):
            mock_client = Mock()
            mock_client.close.return_value = None
            mock_create.return_value = mock_client

            health = await AsyncPulsarMemvidAdapter.health_check(
                "pulsar://localhost:6650"
            )

            assert health["healthy"] is True
            assert health["pulsar_connection"] == "ok"
            assert health["dependencies"] == "ok"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        with patch.object(
            AsyncPulsarMemvidAdapter,
            "_import_dependencies",
            side_effect=ConnectionError("Dependencies missing"),
        ):
            health = await AsyncPulsarMemvidAdapter.health_check(
                "pulsar://localhost:6650"
            )

            assert health["healthy"] is False
            assert "error" in health


class TestPulsarMemvidMessage:
    """Test PulsarMemvidMessage model."""

    def test_message_creation(self):
        """Test creating a PulsarMemvidMessage."""
        msg = PulsarMemvidMessage(
            message_id="test-id",
            timestamp=datetime.now(),
            operation="encode",
            payload={"test": "data"},
            memory_id="memory-1",
        )

        assert msg.message_id == "test-id"
        assert msg.operation == "encode"
        assert msg.payload == {"test": "data"}
        assert msg.memory_id == "memory-1"

    def test_message_serialization(self):
        """Test message JSON serialization."""
        msg = PulsarMemvidMessage(
            message_id="test-id",
            timestamp=datetime.now(),
            operation="search",
            payload={"query": "test"},
            memory_id="memory-1",
        )

        json_data = msg.model_dump_json()
        assert isinstance(json_data, str)

        # Test deserialization
        parsed = PulsarMemvidMessage.model_validate_json(json_data)
        assert parsed.message_id == msg.message_id
        assert parsed.operation == msg.operation


class TestMemoryOperationResult:
    """Test MemoryOperationResult model."""

    def test_success_result(self):
        """Test creating a successful operation result."""
        result = MemoryOperationResult(
            success=True,
            message_id="msg-1",
            memory_id="mem-1",
            operation="encode",
            result_data={"chunks": 10},
            timestamp=datetime.now(),
        )

        assert result.success is True
        assert result.result_data == {"chunks": 10}
        assert result.error is None

    def test_error_result(self):
        """Test creating an error operation result."""
        result = MemoryOperationResult(
            success=False,
            message_id="msg-1",
            memory_id="mem-1",
            operation="search",
            error="File not found",
            timestamp=datetime.now(),
        )

        assert result.success is False
        assert result.error == "File not found"
        assert result.result_data is None
