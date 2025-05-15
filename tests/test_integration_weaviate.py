"""
Integration tests for WeaviateAdapter and AsyncWeaviateAdapter using TestContainers.
"""

import pytest

from pydapter.exceptions import ResourceError
from pydapter.extras.async_weaviate_ import AsyncWeaviateAdapter
from pydapter.extras.weaviate_ import WeaviateAdapter


def is_docker_available():
    """Check if Docker is available."""
    import subprocess

    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# Skip tests if Docker is not available
pytestmark = [
    pytest.mark.skipif(not is_docker_available(), reason="Docker is not available"),
    pytest.mark.asyncio,  # Mark all tests as asyncio
]


@pytest.fixture
def weaviate_cleanup(weaviate_url):
    """Clean up Weaviate database after tests."""
    import urllib.parse

    import weaviate

    yield

    # Cleanup after test
    # Parse URL to extract host and port
    parsed_url = urllib.parse.urlparse(weaviate_url)
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 8080

    # Connect to Weaviate using v4 API
    client = weaviate.connect_to_custom(
        http_host=host,
        http_port=port,
        http_secure=parsed_url.scheme == "https",
        grpc_host=host,
        grpc_port=50051,  # Default gRPC port
        grpc_secure=parsed_url.scheme == "https",
        skip_init_checks=True,  # Skip gRPC health check
    )

    # Delete test classes
    try:
        client.schema.delete_class("TestModel")
    except:
        pass

    try:
        client.schema.delete_class("BatchTest")
    except:
        pass

    try:
        client.schema.delete_class("EmptyClass")
    except:
        pass


@pytest.fixture
async def async_weaviate_cleanup(weaviate_client):
    """Clean up Weaviate database after async tests."""
    yield

    # Cleanup after test using the client from the fixture
    # Delete test classes
    try:
        weaviate_client.schema.delete_class("TestModel")
    except:
        pass

    try:
        weaviate_client.schema.delete_class("BatchTest")
    except:
        pass

    try:
        weaviate_client.schema.delete_class("EmptyClass")
    except:
        pass


class TestWeaviateIntegration:
    """Integration tests for WeaviateAdapter."""

    def test_weaviate_single_object(
        self, weaviate_url, sync_vector_model_factory, weaviate_cleanup
    ):
        """Test WeaviateAdapter with a single object."""
        # Create test instance
        test_model = sync_vector_model_factory(id=44, name="test_weaviate", value=90.12)

        # Register adapter
        test_model.__class__.register_adapter(WeaviateAdapter)

        # Store in database
        test_model.adapt_to(
            obj_key="weav",
            url=weaviate_url,
            class_name="TestModel",
            vector_field="embedding",
        )

        # Retrieve from database
        retrieved = test_model.__class__.adapt_from(
            {
                "url": weaviate_url,
                "class_name": "TestModel",
                "query_vector": test_model.embedding,
            },
            obj_key="weav",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value
        assert retrieved.embedding == test_model.embedding

    def test_weaviate_batch_operations(
        self, weaviate_url, sync_vector_model_factory, weaviate_cleanup
    ):
        """Test batch operations with WeaviateAdapter."""
        model_cls = sync_vector_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(WeaviateAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            model.adapt_to(
                obj_key="weav",
                url=weaviate_url,
                class_name="BatchTest",
                vector_field="embedding",
            )

        # Retrieve all from database (using the first model's embedding as query vector)
        retrieved = model_cls.adapt_from(
            {
                "url": weaviate_url,
                "class_name": "BatchTest",
                "query_vector": models[0].embedding,
                "top_k": 20,  # Ensure we get all results
            },
            obj_key="weav",
            many=True,
        )

        # Verify all records were stored and retrieved correctly
        assert len(retrieved) == 10

        # Sort by ID for consistent comparison
        retrieved_sorted = sorted(retrieved, key=lambda m: m.id)
        for i, model in enumerate(retrieved_sorted, 1):
            assert model.id == i
            assert model.name == f"batch_{i}"
            assert model.value == i * 1.5

    def test_weaviate_resource_not_found(
        self, weaviate_url, sync_vector_model_factory, weaviate_cleanup
    ):
        """Test handling of resource not found errors."""
        model_cls = sync_vector_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_adapter(WeaviateAdapter)

        # Try to retrieve from non-existent class
        with pytest.raises(ResourceError):
            model_cls.adapt_from(
                {
                    "url": weaviate_url,
                    "class_name": "NonExistentClass",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="weav",
                many=False,
            )

    def test_weaviate_empty_result_many(
        self, weaviate_url, sync_vector_model_factory, weaviate_cleanup
    ):
        """Test handling of empty result sets with many=True."""
        # Create a model instance
        model = sync_vector_model_factory(id=1, name="test", value=1.0)
        model_cls = model.__class__

        # Register adapter
        model_cls.register_adapter(WeaviateAdapter)

        # Create class but don't add any objects
        model.adapt_to(
            obj_key="weav",
            url=weaviate_url,
            class_name="EmptyClass",
            vector_field="embedding",
        )

        # Query for objects with many=True
        result = model_cls.adapt_from(
            {
                "url": weaviate_url,
                "class_name": "EmptyClass",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="weav",
            many=True,
        )

        # Verify empty list is returned
        assert isinstance(result, list)
        assert len(result) == 0


class TestAsyncWeaviateIntegration:
    """Integration tests for AsyncWeaviateAdapter."""

    @pytest.mark.asyncio
    async def test_async_weaviate_single_object(
        self, weaviate_url, async_model_factory, async_weaviate_cleanup
    ):
        """Test AsyncWeaviateAdapter with a single object."""
        # Create test instance
        test_model = async_model_factory(id=44, name="test_async_weaviate", value=90.12)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncWeaviateAdapter)

        # Store in database
        await test_model.adapt_to_async(
            obj_key="async_weav",
            url=weaviate_url,
            class_name="TestModel",
            vector_field="embedding",
        )

        # Retrieve from database
        retrieved = await test_model.__class__.adapt_from_async(
            {
                "url": weaviate_url,
                "class_name": "TestModel",
                "query_vector": test_model.embedding,
            },
            obj_key="async_weav",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value
        assert retrieved.embedding == test_model.embedding

    @pytest.mark.asyncio
    async def test_async_weaviate_batch_operations(
        self, weaviate_url, async_model_factory, async_weaviate_cleanup
    ):
        """Test batch operations with AsyncWeaviateAdapter."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            await model.adapt_to_async(
                obj_key="async_weav",
                url=weaviate_url,
                class_name="BatchTest",
                vector_field="embedding",
            )

        # Retrieve all from database (using the first model's embedding as query vector)
        retrieved = await model_cls.adapt_from_async(
            {
                "url": weaviate_url,
                "class_name": "BatchTest",
                "query_vector": models[0].embedding,
                "top_k": 20,  # Ensure we get all results
            },
            obj_key="async_weav",
            many=True,
        )

        # Verify all records were stored and retrieved correctly
        assert len(retrieved) == 10

        # Sort by ID for consistent comparison
        retrieved_sorted = sorted(retrieved, key=lambda m: m.id)
        for i, model in enumerate(retrieved_sorted, 1):
            assert model.id == i
            assert model.name == f"batch_{i}"
            assert model.value == i * 1.5

    @pytest.mark.asyncio
    async def test_async_weaviate_resource_not_found(
        self, weaviate_url, async_model_factory, async_weaviate_cleanup
    ):
        """Test handling of resource not found errors."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Try to retrieve from non-existent class
        with pytest.raises(ResourceError):
            await model_cls.adapt_from_async(
                {
                    "url": weaviate_url,
                    "class_name": "NonExistentClass",
                    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                },
                obj_key="async_weav",
                many=False,
            )

    @pytest.mark.asyncio
    async def test_async_weaviate_empty_result_many(
        self, weaviate_url, async_model_factory, async_weaviate_cleanup
    ):
        """Test handling of empty result sets with many=True."""
        # Create a model instance
        model = async_model_factory(id=1, name="test", value=1.0)
        model_cls = model.__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncWeaviateAdapter)

        # Create class but don't add any objects
        await model.adapt_to_async(
            obj_key="async_weav",
            url=weaviate_url,
            class_name="EmptyClass",
            vector_field="embedding",
        )

        # Query for objects with many=True
        result = await model_cls.adapt_from_async(
            {
                "url": weaviate_url,
                "class_name": "EmptyClass",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            },
            obj_key="async_weav",
            many=True,
        )

        # Verify empty list is returned
        assert isinstance(result, list)
        assert len(result) == 0
