"""
Async Pulsar-enhanced Memvid adapter - combines `memvid` with Apache Pulsar for enterprise streaming.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..async_core import AsyncAdapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError

T = TypeVar("T", bound=BaseModel)


class PulsarMemvidMessage(BaseModel):
    """Message schema for Pulsar-Memvid communication."""

    message_id: str
    timestamp: datetime
    operation: str  # "encode", "search", "update", "rebuild"
    payload: dict[str, Any]
    memory_id: str
    source: str | None = None
    metadata: dict[str, Any] | None = None


class MemoryOperationResult(BaseModel):
    """Result of a memory operation."""

    success: bool
    message_id: str
    memory_id: str
    operation: str
    result_data: dict[str, Any] | None = None
    error: str | None = None
    timestamp: datetime


class AsyncPulsarMemvidAdapter(AsyncAdapter[T]):
    """
    Advanced Pulsar-enhanced Memvid adapter for enterprise streaming AI memory.

    This adapter provides enterprise-grade capabilities:
    - Real-time streaming video memory creation via Pulsar topics
    - Event-driven memory updates and rebuilds
    - Distributed search query processing
    - Multi-tenant memory isolation
    - Fault-tolerant operations with message persistence
    - Horizontal scaling across multiple nodes
    - Live memory synchronization across environments

    Attributes:
        obj_key: The key identifier for this adapter type ("pulsar_memvid")

    Example:
        ```python
        import asyncio
        from pydantic import BaseModel
        from pydapter.extras.async_memvid_pulsar import AsyncPulsarMemvidAdapter

        class Document(BaseModel):
            id: str
            text: str
            category: str
            source: str

        async def main():
            # Stream documents for video memory creation
            docs = [Document(id="1", text="AI content", category="tech", source="blog")]

            stream_config = {
                "pulsar_url": "pulsar://localhost:6650",
                "topic": "memory-updates",
                "memory_id": "ai-knowledge-base",
                "video_file": "memories/ai_memory.mp4",
                "index_file": "memories/ai_index.json"
            }

            # Stream encode operation
            await AsyncPulsarMemvidAdapter.to_obj(docs, stream_config, many=True)

            # Stream search operation
            search_config = {
                "pulsar_url": "pulsar://localhost:6650",
                "search_topic": "search-queries",
                "result_topic": "search-results",
                "memory_id": "ai-knowledge-base",
                "query": "artificial intelligence content"
            }

            results = await AsyncPulsarMemvidAdapter.from_obj(
                Document, search_config, many=True
            )

        asyncio.run(main())
        ```
    """

    obj_key = "pulsar_memvid"

    @staticmethod
    async def _import_dependencies():
        """Import required dependencies with proper error handling."""
        try:
            import pulsar
            from memvid import MemvidEncoder, MemvidRetriever

            return pulsar, MemvidEncoder, MemvidRetriever
        except ImportError as e:
            missing_lib = "pulsar-client" if "pulsar" in str(e) else "memvid"
            raise ConnectionError(
                f"Failed to import {missing_lib}: {e}. Install with: pip install {missing_lib}",
                adapter="pulsar_memvid",
            ) from e

    @staticmethod
    async def _create_pulsar_client(pulsar_url: str, **client_kwargs):
        """Create Pulsar client with connection validation."""
        pulsar, _, _ = await AsyncPulsarMemvidAdapter._import_dependencies()

        try:
            client = pulsar.Client(
                service_url=pulsar_url, operation_timeout_seconds=30, **client_kwargs
            )
            return client
        except Exception as e:
            raise ConnectionError(
                f"Failed to create Pulsar client: {e}",
                adapter="pulsar_memvid",
                url=pulsar_url,
            ) from e

    @classmethod
    async def _create_producer(cls, client, topic: str, **producer_kwargs):
        """Create Pulsar producer with error handling."""
        try:
            # Build producer config
            producer_config = {
                "topic": topic,
                "batching_enabled": True,
                **producer_kwargs,
            }

            # Only add compression_type if CompressionType is available
            if hasattr(client, "CompressionType"):
                producer_config["compression_type"] = client.CompressionType.LZ4

            producer = client.create_producer(**producer_config)
            return producer
        except Exception as e:
            raise ConnectionError(
                f"Failed to create Pulsar producer for topic '{topic}': {e}",
                adapter="pulsar_memvid",
            ) from e

    @classmethod
    async def _create_consumer(
        cls, client, topic: str, subscription: str, **consumer_kwargs
    ):
        """Create Pulsar consumer with error handling."""
        try:
            # Build consumer config
            consumer_config = {
                "topic": topic,
                "subscription_name": subscription,
                **consumer_kwargs,
            }

            # Only add consumer_type if ConsumerType is available
            if hasattr(client, "ConsumerType"):
                consumer_config["consumer_type"] = client.ConsumerType.Shared

            consumer = client.subscribe(**consumer_config)
            return consumer
        except Exception as e:
            raise ConnectionError(
                f"Failed to create Pulsar consumer for topic '{topic}': {e}",
                adapter="pulsar_memvid",
            ) from e

    @classmethod
    async def _process_memory_operation(
        cls,
        operation: str,
        payload: dict[str, Any],
        memory_id: str,
        video_file: str,
        index_file: str,
    ) -> MemoryOperationResult:
        """Process a memory operation (encode, search, update, rebuild)."""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now()

        try:
            _, MemvidEncoder, MemvidRetriever = await cls._import_dependencies()

            if operation == "encode":
                # Create video memory from text chunks
                encoder = MemvidEncoder()

                for chunk_data in payload.get("chunks", []):
                    text = chunk_data.get("text", "")
                    chunk_size = payload.get("chunk_size", 1024)
                    overlap = payload.get("overlap", 32)

                    if text:
                        encoder.add_text(text, chunk_size=chunk_size, overlap=overlap)

                if encoder.get_stats().get("total_chunks", 0) > 0:
                    stats = encoder.build_video(
                        video_file,
                        index_file,
                        codec=payload.get("codec", "h265"),
                        show_progress=False,
                        allow_fallback=True,
                    )

                    return MemoryOperationResult(
                        success=True,
                        message_id=message_id,
                        memory_id=memory_id,
                        operation=operation,
                        result_data={
                            "encoded_chunks": encoder.get_stats().get(
                                "total_chunks", 0
                            ),
                            "video_file": video_file,
                            "index_file": index_file,
                            **stats,
                        },
                        timestamp=timestamp,
                    )
                else:
                    return MemoryOperationResult(
                        success=False,
                        message_id=message_id,
                        memory_id=memory_id,
                        operation=operation,
                        error="No chunks to encode",
                        timestamp=timestamp,
                    )

            elif operation == "search":
                # Search video memory
                if not Path(video_file).exists() or not Path(index_file).exists():
                    return MemoryOperationResult(
                        success=False,
                        message_id=message_id,
                        memory_id=memory_id,
                        operation=operation,
                        error=f"Memory files not found: {video_file}, {index_file}",
                        timestamp=timestamp,
                    )

                retriever = MemvidRetriever(video_file, index_file)
                query = payload.get("query", "")
                top_k = payload.get("top_k", 5)

                if query:
                    results = retriever.search_with_metadata(query, top_k=top_k)

                    return MemoryOperationResult(
                        success=True,
                        message_id=message_id,
                        memory_id=memory_id,
                        operation=operation,
                        result_data={
                            "query": query,
                            "results": results,
                            "result_count": len(results),
                        },
                        timestamp=timestamp,
                    )
                else:
                    return MemoryOperationResult(
                        success=False,
                        message_id=message_id,
                        memory_id=memory_id,
                        operation=operation,
                        error="No query provided",
                        timestamp=timestamp,
                    )

            elif operation == "update":
                # Incremental update to existing memory
                # This would be more complex - for now, rebuild entire memory
                return await cls._process_memory_operation(
                    "encode", payload, memory_id, video_file, index_file
                )

            elif operation == "rebuild":
                # Full memory rebuild
                return await cls._process_memory_operation(
                    "encode", payload, memory_id, video_file, index_file
                )

            else:
                return MemoryOperationResult(
                    success=False,
                    message_id=message_id,
                    memory_id=memory_id,
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    timestamp=timestamp,
                )

        except Exception as e:
            return MemoryOperationResult(
                success=False,
                message_id=message_id,
                memory_id=memory_id,
                operation=operation,
                error=str(e),
                timestamp=timestamp,
            )

    # outgoing - stream data to Pulsar for video memory creation
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        pulsar_url: str,
        topic: str,
        memory_id: str,
        video_file: str,
        index_file: str,
        text_field: str = "text",
        chunk_size: int = 1024,
        overlap: int = 32,
        codec: str = "h265",
        operation: str = "encode",
        async_processing: bool = True,
        result_topic: str | None = None,
        many: bool = True,
        adapt_meth: str = "model_dump",
        **_kw,
    ) -> dict[str, Any]:
        """
        Stream data to Pulsar for distributed video memory creation.

        Args:
            subj: Pydantic model(s) to encode into video memory
            pulsar_url: Pulsar service URL (e.g., "pulsar://localhost:6650")
            topic: Pulsar topic for memory operations
            memory_id: Unique identifier for this memory instance
            video_file: Path to output video file
            index_file: Path to output index file
            text_field: Field name containing text content
            chunk_size: Text chunk size for encoding
            overlap: Overlap between chunks
            codec: Video codec to use
            operation: Operation type ("encode", "update", "rebuild")
            async_processing: Whether to process asynchronously
            result_topic: Topic to publish results (if async_processing=True)
        """
        try:
            # Validate required parameters
            if not pulsar_url:
                raise ValidationError("Missing required parameter 'pulsar_url'")
            if not topic:
                raise ValidationError("Missing required parameter 'topic'")
            if not memory_id:
                raise ValidationError("Missing required parameter 'memory_id'")
            if not video_file:
                raise ValidationError("Missing required parameter 'video_file'")
            if not index_file:
                raise ValidationError("Missing required parameter 'index_file'")

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"message_count": 0, "memory_id": memory_id}

            # Validate text field exists
            if not hasattr(items[0], text_field):
                raise ValidationError(
                    f"Text field '{text_field}' not found in model",
                    data=getattr(items[0], adapt_meth)(),
                )

            # Create Pulsar client and producer
            client = await cls._create_pulsar_client(pulsar_url)
            producer = await cls._create_producer(client, topic)

            try:
                # Prepare chunks from models
                chunks = []
                for item in items:
                    text = getattr(item, text_field)
                    if not isinstance(text, str):
                        raise ValidationError(
                            f"Text field '{text_field}' must be a string",
                            data=text,
                        )

                    chunk_data = {"text": text, "metadata": getattr(item, adapt_meth)()}
                    chunks.append(chunk_data)

                # Create Pulsar message
                message = PulsarMemvidMessage(
                    message_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    operation=operation,
                    payload={
                        "chunks": chunks,
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "codec": codec,
                        "video_file": video_file,
                        "index_file": index_file,
                    },
                    memory_id=memory_id,
                    source="pydapter",
                    metadata={
                        "item_count": len(items),
                        "text_field": text_field,
                        "async_processing": async_processing,
                    },
                )

                # Send message to Pulsar
                message_data = getattr(message, adapt_meth + "_json")().encode("utf-8")
                msg_id = producer.send(
                    content=message_data,
                    properties={
                        "memory_id": memory_id,
                        "operation": operation,
                        "message_id": message.message_id,
                    },
                )

                result = {
                    "message_sent": True,
                    "message_id": message.message_id,
                    "pulsar_message_id": str(msg_id),
                    "memory_id": memory_id,
                    "operation": operation,
                    "item_count": len(items),
                    "async_processing": async_processing,
                }

                # If not async, process immediately
                if not async_processing:
                    operation_result = await cls._process_memory_operation(
                        operation=operation,
                        payload=message.payload,
                        memory_id=memory_id,
                        video_file=video_file,
                        index_file=index_file,
                    )

                    result.update(
                        {
                            "operation_result": getattr(operation_result, adapt_meth)(),
                            "success": operation_result.success,
                        }
                    )

                    # Publish result if result topic provided
                    if result_topic and operation_result.success:
                        result_producer = await cls._create_producer(
                            client, result_topic
                        )
                        try:
                            result_data = getattr(
                                operation_result, adapt_meth + "_json"
                            )().encode("utf-8")
                            result_producer.send(
                                content=result_data,
                                properties={
                                    "memory_id": memory_id,
                                    "operation": operation,
                                    "message_id": message.message_id,
                                    "success": str(operation_result.success),
                                },
                            )
                        finally:
                            result_producer.close()

                return result

            finally:
                producer.close()
                client.close()

        except (ConnectionError, QueryError, ValidationError):
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in Pulsar Memvid adapter: {e}",
                adapter="pulsar_memvid",
            )

    # incoming - consume search queries from Pulsar and return results
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        adapt_meth: str = "model_validate",
        **_kw,
    ) -> list[T] | T | None:
        """
        Consume search queries from Pulsar and return model instances.

        Args:
            subj_cls: Pydantic model class for results
            obj: Configuration dictionary containing:
                - pulsar_url: Pulsar service URL
                - search_topic: Topic to consume search queries from
                - memory_id: Memory instance identifier
                - query: Search query (for direct search)
                - subscription: Consumer subscription name
                - timeout_ms: Consumer timeout in milliseconds
                - video_file: Video memory file path
                - index_file: Index file path
            many: Whether to return multiple results
        """
        try:
            # Validate required parameters
            if "pulsar_url" not in obj:
                raise ValidationError(
                    "Missing required parameter 'pulsar_url'", data=obj
                )

            # Handle direct search vs streaming consumption
            if "query" in obj:
                # Direct search mode
                return await cls._direct_search(
                    subj_cls, obj, many=many, adapt_meth=adapt_meth
                )
            else:
                # Streaming consumption mode
                return await cls._stream_search(
                    subj_cls, obj, many=many, adapt_meth=adapt_meth
                )

        except (ConnectionError, QueryError, ResourceError, ValidationError):
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in Pulsar Memvid adapter: {e}",
                adapter="pulsar_memvid",
            )

    @classmethod
    async def _direct_search(
        cls,
        subj_cls: type[T],
        obj: dict,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
    ) -> list[T] | T | None:
        """Perform direct search without Pulsar streaming."""
        if "video_file" not in obj or "index_file" not in obj:
            raise ValidationError(
                "Missing required parameters 'video_file' and 'index_file' for direct search",
                data=obj,
            )

        memory_id = obj.get("memory_id", "default")
        operation_result = await cls._process_memory_operation(
            operation="search",
            payload={"query": obj["query"], "top_k": obj.get("top_k", 5)},
            memory_id=memory_id,
            video_file=obj["video_file"],
            index_file=obj["index_file"],
        )

        if not operation_result.success:
            if many:
                return []
            raise ResourceError(
                f"Search failed: {operation_result.error}",
                resource=f"{obj['video_file']}, {obj['index_file']}",
            )

        # Convert results to model instances
        search_results = operation_result.result_data.get("results", [])
        if not search_results:
            if many:
                return []
            raise ResourceError(
                "No results found for query",
                resource=obj["video_file"],
                query=obj["query"],
            )

        try:
            instances = []
            for i, result in enumerate(search_results):
                text_content = result.get("text", "")

                # Create model instance
                model_data = {
                    "id": str(i),
                    "text": text_content,
                }

                try:
                    instance = getattr(subj_cls, adapt_meth)(model_data)
                    instances.append(instance)
                except PydanticValidationError:
                    # Fallback for different model structures
                    minimal_data = {"text": text_content}
                    instance = getattr(subj_cls, adapt_meth)(minimal_data)
                    instances.append(instance)

            if many:
                return instances
            return instances[0] if instances else None

        except PydanticValidationError as e:
            raise ValidationError(
                f"Validation error converting search results: {e}",
                data=search_results[0] if search_results else None,
            ) from e

    @classmethod
    async def _stream_search(
        cls,
        subj_cls: type[T],
        obj: dict,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
    ) -> list[T] | T | None:
        """Consume search queries from Pulsar stream."""
        if "search_topic" not in obj:
            raise ValidationError(
                "Missing required parameter 'search_topic' for streaming search",
                data=obj,
            )

        # Create Pulsar client and consumer
        client = await cls._create_pulsar_client(obj["pulsar_url"])
        subscription = obj.get("subscription", f"search-{uuid.uuid4()}")
        consumer = await cls._create_consumer(client, obj["search_topic"], subscription)

        try:
            # Receive message from stream
            timeout_ms = obj.get("timeout_ms", 10000)

            try:
                msg = consumer.receive(timeout_millis=timeout_ms)

                # Parse message
                message_data = json.loads(msg.data().decode("utf-8"))
                pulsar_message = PulsarMemvidMessage.model_validate(message_data)

                # Acknowledge message
                consumer.acknowledge(msg)

                # Process search if it's a search operation
                if pulsar_message.operation == "search":
                    payload = pulsar_message.payload
                    memory_id = pulsar_message.memory_id

                    # Need video/index files from payload or config
                    video_file = payload.get("video_file") or obj.get("video_file")
                    index_file = payload.get("index_file") or obj.get("index_file")

                    if not video_file or not index_file:
                        raise ValidationError(
                            "Missing video_file or index_file in message payload or config"
                        )

                    # Perform search
                    operation_result = await cls._process_memory_operation(
                        operation="search",
                        payload=payload,
                        memory_id=memory_id,
                        video_file=video_file,
                        index_file=index_file,
                    )

                    if operation_result.success:
                        search_results = operation_result.result_data.get("results", [])

                        # Convert to model instances (similar to direct search)
                        instances = []
                        for i, result in enumerate(search_results):
                            text_content = result.get("text", "")
                            model_data = {"id": str(i), "text": text_content}

                            try:
                                instance = getattr(subj_cls, adapt_meth)(model_data)
                                instances.append(instance)
                            except PydanticValidationError:
                                minimal_data = {"text": text_content}
                                instance = getattr(subj_cls, adapt_meth)(minimal_data)
                                instances.append(instance)

                        if many:
                            return instances
                        return instances[0] if instances else None
                    else:
                        raise QueryError(
                            f"Search operation failed: {operation_result.error}",
                            adapter="pulsar_memvid",
                        )
                else:
                    raise ValidationError(
                        f"Expected search operation, got: {pulsar_message.operation}"
                    )

            except Exception as receive_error:
                if "timeout" in str(receive_error).lower():
                    if many:
                        return []
                    raise ResourceError(
                        "No search queries received within timeout",
                        resource=obj["search_topic"],
                    )
                raise

        finally:
            consumer.close()
            client.close()

    @classmethod
    async def create_memory_worker(
        cls,
        pulsar_url: str,
        topic: str,
        subscription: str,
        result_topic: str | None = None,
        worker_id: str | None = None,
    ) -> Callable:
        """
        Create a background worker that processes memory operations from Pulsar.

        Returns a callable that can be used with asyncio.create_task() for background processing.
        """

        async def worker():
            worker_name = worker_id or f"memvid-worker-{uuid.uuid4()}"
            client = await cls._create_pulsar_client(pulsar_url)
            consumer = await cls._create_consumer(client, topic, subscription)

            result_producer = None
            if result_topic:
                result_producer = await cls._create_producer(client, result_topic)

            try:
                while True:
                    try:
                        # Receive message
                        msg = consumer.receive(timeout_millis=5000)

                        # Parse message
                        message_data = json.loads(msg.data().decode("utf-8"))
                        pulsar_message = PulsarMemvidMessage.model_validate(
                            message_data
                        )

                        # Process operation
                        payload = pulsar_message.payload
                        operation_result = await cls._process_memory_operation(
                            operation=pulsar_message.operation,
                            payload=payload,
                            memory_id=pulsar_message.memory_id,
                            video_file=payload.get("video_file", ""),
                            index_file=payload.get("index_file", ""),
                        )

                        # Acknowledge message
                        consumer.acknowledge(msg)

                        # Publish result if result topic configured
                        if result_producer and operation_result:
                            result_data = operation_result.model_dump_json().encode(
                                "utf-8"
                            )
                            result_producer.send(
                                content=result_data,
                                properties={
                                    "memory_id": pulsar_message.memory_id,
                                    "operation": pulsar_message.operation,
                                    "message_id": pulsar_message.message_id,
                                    "worker_id": worker_name,
                                    "success": str(operation_result.success),
                                },
                            )

                    except Exception as e:
                        # Log error but continue processing
                        print(f"Worker {worker_name} error: {e}")
                        await asyncio.sleep(1)

            except asyncio.CancelledError:
                # Graceful shutdown
                pass
            finally:
                if result_producer:
                    result_producer.close()
                consumer.close()
                client.close()

        return worker

    @classmethod
    async def health_check(cls, pulsar_url: str) -> dict[str, Any]:
        """Check health of Pulsar connection and dependencies."""
        try:
            # Check dependencies
            await cls._import_dependencies()

            # Check Pulsar connection
            client = await cls._create_pulsar_client(pulsar_url)
            client.close()

            return {
                "healthy": True,
                "pulsar_connection": "ok",
                "dependencies": "ok",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
