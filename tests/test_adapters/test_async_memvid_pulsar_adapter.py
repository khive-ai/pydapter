"""
Comprehensive tests for AsyncPulsarMemvidAdapter functionality.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import (
    ValidationError,
    ConnectionError,
)
from pydapter.extras.async_memvid_pulsar import (
    AsyncPulsarMemvidAdapter,
    PulsarMemvidMessage,
    MemoryOperationResult,
)


@pytest.fixture
def pulsar_memvid_model_factory():
    """Factory for creating test models with AsyncPulsarMemvidAdapter registered."""

    def create_model(**kw):
        class TestDocument(AsyncAdaptable, BaseModel):
            id: str
            text: str
            category: str = "general"
            source: str = "test"

        # Register the adapter
        TestDocument.register_adapter(AsyncPulsarMemvidAdapter)
        return TestDocument(**kw)

    return create_model


@pytest.fixture
def sample_document(pulsar_memvid_model_factory):
    """Create a sample document instance."""
    return pulsar_memvid_model_factory(
        id="doc1",
        text="This is sample content for testing Pulsar-Memvid adapter functionality.",
        category="test",
        source="unit_test",
    )


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_file = Path(tmpdir) / "test_memory.mp4"
        index_file = Path(tmpdir) / "test_index.json"
        yield str(video_file), str(index_file)


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client for testing."""
    mock_client = Mock()
    mock_producer = Mock()
    mock_consumer = Mock()

    # Setup producer mock
    mock_producer.send.return_value = "test-message-id"
    mock_producer.close.return_value = None

    # Setup consumer mock
    mock_message = Mock()
    mock_message.data.return_value = json.dumps(
        {
            "message_id": "test-msg-id",
            "timestamp": datetime.now().isoformat(),
            "operation": "search",
            "payload": {
                "query": "test query",
                "top_k": 5,
                "video_file": "test.mp4",
                "index_file": "test.json",
            },
            "memory_id": "test-memory",
            "source": "test",
            "metadata": {},
        }
    ).encode("utf-8")

    mock_consumer.receive.return_value = mock_message
    mock_consumer.acknowledge.return_value = None
    mock_consumer.close.return_value = None

    # Setup client mock
    mock_client.create_producer.return_value = mock_producer
    mock_client.subscribe.return_value = mock_consumer
    mock_client.close.return_value = None

    return mock_client


class TestAsyncPulsarMemvidAdapterProtocol:
    """Tests for AsyncPulsarMemvidAdapter protocol compliance."""

    def test_adapter_protocol_compliance(self):
        """Test that AsyncPulsarMemvidAdapter implements the AsyncAdapter protocol."""
        # Verify required attributes
        assert hasattr(AsyncPulsarMemvidAdapter, "obj_key")
        assert isinstance(AsyncPulsarMemvidAdapter.obj_key, str)
        assert AsyncPulsarMemvidAdapter.obj_key == "pulsar_memvid"

        # Verify method signatures
        assert hasattr(AsyncPulsarMemvidAdapter, "from_obj")
        assert hasattr(AsyncPulsarMemvidAdapter, "to_obj")


class TestPulsarMemvidMessage:
    """Tests for PulsarMemvidMessage model."""

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
    """Tests for MemoryOperationResult model."""

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


class TestAsyncPulsarMemvidAdapterDependencies:
    """Tests for dependency import handling."""

    @pytest.mark.asyncio
    async def test_import_dependencies_success(self):
        """Test successful dependency import."""
        with (
            patch("pulsar.Client"),
            patch("memvid.MemvidEncoder"),
            patch("memvid.MemvidRetriever"),
        ):
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
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'pulsar'")
        ):
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


class TestAsyncPulsarMemvidAdapterClient:
    """Tests for Pulsar client creation and management."""

    @pytest.mark.asyncio
    async def test_create_pulsar_client_success(self):
        """Test successful Pulsar client creation."""
        with patch("pulsar.Client") as mock_pulsar_class:
            mock_client = Mock()
            mock_pulsar_class.return_value = mock_client

            with patch.object(
                AsyncPulsarMemvidAdapter,
                "_import_dependencies",
                return_value=(mock_pulsar_class, Mock(), Mock()),
            ):
                client = await AsyncPulsarMemvidAdapter._create_pulsar_client(
                    "pulsar://localhost:6650"
                )

                assert client is mock_client
                mock_pulsar_class.assert_called_once_with(
                    service_url="pulsar://localhost:6650", operation_timeout_seconds=30
                )

    @pytest.mark.asyncio
    async def test_create_pulsar_client_failure(self):
        """Test Pulsar client creation failure."""
        with patch.object(
            AsyncPulsarMemvidAdapter,
            "_import_dependencies",
            return_value=(Mock(), Mock(), Mock()),
        ):
            with patch("pulsar.Client", side_effect=Exception("Connection failed")):
                with pytest.raises(ConnectionError) as exc_info:
                    await AsyncPulsarMemvidAdapter._create_pulsar_client("invalid-url")

                assert "Failed to create Pulsar client" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_producer_success(self, mock_pulsar_client):
        """Test successful producer creation."""
        producer = await AsyncPulsarMemvidAdapter._create_producer(
            mock_pulsar_client, "test-topic"
        )

        assert producer is not None
        mock_pulsar_client.create_producer.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_consumer_success(self, mock_pulsar_client):
        """Test successful consumer creation."""
        consumer = await AsyncPulsarMemvidAdapter._create_consumer(
            mock_pulsar_client, "test-topic", "test-subscription"
        )

        assert consumer is not None
        mock_pulsar_client.subscribe.assert_called_once()


class TestAsyncPulsarMemvidAdapterMemoryOperations:
    """Tests for memory operations (encode, search, update, rebuild)."""

    @pytest.mark.asyncio
    async def test_process_memory_operation_encode_success(self, temp_files):
        """Test successful encode operation."""
        video_file, index_file = temp_files

        with patch.object(
            AsyncPulsarMemvidAdapter, "_import_dependencies"
        ) as mock_deps:
            mock_encoder = Mock()
            mock_encoder.add_text.return_value = None
            mock_encoder.get_stats.return_value = {"total_chunks": 3}
            mock_encoder.build_video.return_value = {"chunks": 3, "frames": 100}

            mock_deps.return_value = (Mock(), lambda: mock_encoder, Mock())

            result = await AsyncPulsarMemvidAdapter._process_memory_operation(
                operation="encode",
                payload={
                    "chunks": [{"text": "Sample text 1"}, {"text": "Sample text 2"}],
                    "chunk_size": 512,
                    "overlap": 32,
                },
                memory_id="test-memory",
                video_file=video_file,
                index_file=index_file,
            )

            assert result.success is True
            assert result.operation == "encode"
            assert result.result_data["encoded_chunks"] == 3

    @pytest.mark.asyncio
    async def test_process_memory_operation_search_success(self, temp_files):
        """Test successful search operation."""
        video_file, index_file = temp_files

        # Create dummy files
        Path(video_file).touch()
        Path(index_file).touch()

        with patch.object(
            AsyncPulsarMemvidAdapter, "_import_dependencies"
        ) as mock_deps:
            mock_retriever = Mock()
            mock_retriever.search_with_metadata.return_value = [
                {"text": "Found content", "score": 0.95}
            ]

            mock_deps.return_value = (Mock(), Mock(), lambda *args: mock_retriever)

            result = await AsyncPulsarMemvidAdapter._process_memory_operation(
                operation="search",
                payload={"query": "test query", "top_k": 5},
                memory_id="test-memory",
                video_file=video_file,
                index_file=index_file,
            )

            assert result.success is True
            assert result.operation == "search"
            assert len(result.result_data["results"]) == 1

    @pytest.mark.asyncio
    async def test_process_memory_operation_search_files_not_found(self):
        """Test search operation when memory files don't exist."""
        result = await AsyncPulsarMemvidAdapter._process_memory_operation(
            operation="search",
            payload={"query": "test"},
            memory_id="test-memory",
            video_file="nonexistent.mp4",
            index_file="nonexistent.json",
        )

        assert result.success is False
        assert "Memory files not found" in result.error

    @pytest.mark.asyncio
    async def test_process_memory_operation_unknown_operation(self, temp_files):
        """Test handling of unknown operation."""
        video_file, index_file = temp_files

        result = await AsyncPulsarMemvidAdapter._process_memory_operation(
            operation="invalid_op",
            payload={},
            memory_id="test-memory",
            video_file=video_file,
            index_file=index_file,
        )

        assert result.success is False
        assert "Unknown operation: invalid_op" in result.error


class TestAsyncPulsarMemvidAdapterToObj:
    """Tests for AsyncPulsarMemvidAdapter.to_obj (streaming encoding)."""

    @pytest.mark.asyncio
    async def test_to_obj_validation_errors(self):
        """Test validation errors for required parameters."""
        sample = Mock()

        # Missing pulsar_url
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.to_obj(
                sample,
                topic="test",
                memory_id="mem1",
                video_file="test.mp4",
                index_file="test.json",
            )
        assert "Missing required parameter 'pulsar_url'" in str(exc_info.value)

        # Missing topic
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.to_obj(
                sample,
                pulsar_url="pulsar://localhost:6650",
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
    async def test_to_obj_async_processing_success(
        self, sample_document, mock_pulsar_client
    ):
        """Test successful async processing."""
        with (
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_pulsar_client",
                return_value=mock_pulsar_client,
            ),
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_producer",
                return_value=mock_pulsar_client.create_producer(),
            ),
        ):
            result = await AsyncPulsarMemvidAdapter.to_obj(
                sample_document,
                pulsar_url="pulsar://localhost:6650",
                topic="memory-updates",
                memory_id="test-memory",
                video_file="test.mp4",
                index_file="test.json",
                async_processing=True,
            )

            assert result["message_sent"] is True
            assert result["memory_id"] == "test-memory"
            assert result["operation"] == "encode"
            assert result["async_processing"] is True

    @pytest.mark.asyncio
    async def test_to_obj_sync_processing_success(
        self, sample_document, mock_pulsar_client, temp_files
    ):
        """Test successful synchronous processing."""
        video_file, index_file = temp_files

        with (
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_pulsar_client",
                return_value=mock_pulsar_client,
            ),
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_producer",
                return_value=mock_pulsar_client.create_producer(),
            ),
            patch.object(
                AsyncPulsarMemvidAdapter, "_process_memory_operation"
            ) as mock_process,
        ):
            # Mock successful operation result
            mock_result = MemoryOperationResult(
                success=True,
                message_id="test-msg",
                memory_id="test-memory",
                operation="encode",
                result_data={"encoded_chunks": 1},
                timestamp=datetime.now(),
            )
            mock_process.return_value = mock_result

            result = await AsyncPulsarMemvidAdapter.to_obj(
                sample_document,
                pulsar_url="pulsar://localhost:6650",
                topic="memory-updates",
                memory_id="test-memory",
                video_file=video_file,
                index_file=index_file,
                async_processing=False,
            )

            assert result["message_sent"] is True
            assert result["success"] is True
            assert "operation_result" in result


class TestAsyncPulsarMemvidAdapterFromObj:
    """Tests for AsyncPulsarMemvidAdapter.from_obj (streaming search)."""

    @pytest.mark.asyncio
    async def test_from_obj_validation_errors(self):
        """Test validation errors for required parameters."""

        # Missing pulsar_url
        with pytest.raises(ValidationError) as exc_info:
            await AsyncPulsarMemvidAdapter.from_obj(
                Mock, {"search_topic": "test", "memory_id": "mem1"}
            )
        assert "Missing required parameter 'pulsar_url'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_from_obj_direct_search_success(
        self, pulsar_memvid_model_factory, temp_files
    ):
        """Test successful direct search."""
        video_file, index_file = temp_files

        # Create dummy files
        Path(video_file).touch()
        Path(index_file).touch()

        TestDoc = pulsar_memvid_model_factory.__wrapped__()

        with patch.object(
            AsyncPulsarMemvidAdapter, "_process_memory_operation"
        ) as mock_process:
            mock_result = MemoryOperationResult(
                success=True,
                message_id="test-msg",
                memory_id="test-memory",
                operation="search",
                result_data={
                    "results": [{"text": "Sample search result", "score": 0.95}]
                },
                timestamp=datetime.now(),
            )
            mock_process.return_value = mock_result

            with patch.object(TestDoc, "model_validate") as mock_validate:
                mock_validate.return_value = Mock(id="0", text="Sample search result")

                result = await AsyncPulsarMemvidAdapter.from_obj(
                    TestDoc,
                    {
                        "pulsar_url": "pulsar://localhost:6650",
                        "query": "test query",
                        "video_file": video_file,
                        "index_file": index_file,
                        "memory_id": "test-memory",
                    },
                    many=True,
                )

                assert len(result) == 1
                mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_from_obj_stream_search_success(
        self, pulsar_memvid_model_factory, mock_pulsar_client, temp_files
    ):
        """Test successful streaming search."""
        video_file, index_file = temp_files

        # Create dummy files
        Path(video_file).touch()
        Path(index_file).touch()

        TestDoc = pulsar_memvid_model_factory.__wrapped__()

        with (
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_pulsar_client",
                return_value=mock_pulsar_client,
            ),
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_consumer",
                return_value=mock_pulsar_client.subscribe(),
            ),
            patch.object(
                AsyncPulsarMemvidAdapter, "_process_memory_operation"
            ) as mock_process,
        ):
            mock_result = MemoryOperationResult(
                success=True,
                message_id="test-msg",
                memory_id="test-memory",
                operation="search",
                result_data={
                    "results": [{"text": "Streaming search result", "score": 0.9}]
                },
                timestamp=datetime.now(),
            )
            mock_process.return_value = mock_result

            with patch.object(TestDoc, "model_validate") as mock_validate:
                mock_validate.return_value = Mock(
                    id="0", text="Streaming search result"
                )

                result = await AsyncPulsarMemvidAdapter.from_obj(
                    TestDoc,
                    {
                        "pulsar_url": "pulsar://localhost:6650",
                        "search_topic": "search-queries",
                        "video_file": video_file,
                        "index_file": index_file,
                    },
                    many=True,
                )

                assert len(result) == 1


class TestAsyncPulsarMemvidAdapterWorker:
    """Tests for background worker functionality."""

    @pytest.mark.asyncio
    async def test_create_memory_worker(self, mock_pulsar_client):
        """Test creating a memory worker."""
        with (
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_pulsar_client",
                return_value=mock_pulsar_client,
            ),
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_consumer",
                return_value=mock_pulsar_client.subscribe(),
            ),
            patch.object(
                AsyncPulsarMemvidAdapter,
                "_create_producer",
                return_value=mock_pulsar_client.create_producer(),
            ),
        ):
            worker_func = await AsyncPulsarMemvidAdapter.create_memory_worker(
                pulsar_url="pulsar://localhost:6650",
                topic="memory-operations",
                subscription="worker-group",
                result_topic="operation-results",
                worker_id="test-worker",
            )

            assert callable(worker_func)

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


class TestAsyncPulsarMemvidAdapterIntegration:
    """Integration tests for AsyncPulsarMemvidAdapter."""

    def test_adapter_registration(self, pulsar_memvid_model_factory):
        """Test that AsyncPulsarMemvidAdapter can be registered with models."""
        doc = pulsar_memvid_model_factory(
            id="test", text="Sample text", source="integration_test"
        )

        # Check that the adapter is registered
        assert hasattr(doc.__class__, "_adapters")
        adapter_keys = [adapter.obj_key for adapter in doc.__class__._adapters]
        assert "pulsar_memvid" in adapter_keys

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_simulation(self, sample_document, temp_files):
        """Test simulated end-to-end workflow without actual Pulsar/Memvid."""
        video_file, index_file = temp_files

        # Mock all external dependencies
        with (
            patch.object(AsyncPulsarMemvidAdapter, "_import_dependencies") as mock_deps,
            patch.object(
                AsyncPulsarMemvidAdapter, "_create_pulsar_client"
            ) as mock_client_create,
            patch.object(
                AsyncPulsarMemvidAdapter, "_create_producer"
            ) as mock_producer_create,
        ):
            # Setup mocks
            mock_encoder = Mock()
            mock_encoder.add_text.return_value = None
            mock_encoder.get_stats.return_value = {"total_chunks": 1}
            mock_encoder.build_video.return_value = {"chunks": 1, "frames": 50}

            mock_retriever = Mock()
            mock_retriever.search_with_metadata.return_value = [
                {"text": "Found content", "score": 0.95}
            ]

            mock_deps.return_value = (
                Mock(),
                lambda: mock_encoder,
                lambda *args: mock_retriever,
            )

            mock_client = Mock()
            mock_producer = Mock()
            mock_producer.send.return_value = "msg-id"
            mock_producer.close.return_value = None
            mock_client.close.return_value = None

            mock_client_create.return_value = mock_client
            mock_producer_create.return_value = mock_producer

            # Test encode operation
            encode_result = await AsyncPulsarMemvidAdapter.to_obj(
                sample_document,
                pulsar_url="pulsar://localhost:6650",
                topic="memory-updates",
                memory_id="test-memory",
                video_file=video_file,
                index_file=index_file,
                async_processing=False,
            )

            assert encode_result["success"] is True
            assert encode_result["message_sent"] is True

            # Create dummy files for search
            Path(video_file).touch()
            Path(index_file).touch()

            # Test search operation
            TestDoc = sample_document.__class__
            with patch.object(TestDoc, "model_validate") as mock_validate:
                mock_validate.return_value = Mock(id="0", text="Found content")

                search_result = await AsyncPulsarMemvidAdapter.from_obj(
                    TestDoc,
                    {
                        "pulsar_url": "pulsar://localhost:6650",
                        "query": "test query",
                        "video_file": video_file,
                        "index_file": index_file,
                        "memory_id": "test-memory",
                    },
                    many=True,
                )

                assert len(search_result) == 1
