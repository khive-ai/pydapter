"""
Integration tests for AsyncNeo4jAdapter using TestContainers.
"""

import pytest
from neo4j import AsyncGraphDatabase

from pydapter.exceptions import ConnectionError, ResourceError
from pydapter.extras.async_neo4j_ import AsyncNeo4jAdapter


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
async def async_neo4j_cleanup(neo4j_url, neo4j_auth):
    """Clean up Neo4j database before and after tests."""
    # Cleanup before test
    driver = AsyncGraphDatabase.driver(neo4j_url, auth=neo4j_auth)
    async with driver:
        async with driver.session() as session:
            # Delete all nodes with TestModel label
            await session.run("MATCH (n:TestModel) DETACH DELETE n")
            # Delete all nodes with BatchTest label
            await session.run("MATCH (n:BatchTest) DETACH DELETE n")
    
    yield

    # Cleanup after test
    driver = AsyncGraphDatabase.driver(neo4j_url, auth=neo4j_auth)
    async with driver:
        async with driver.session() as session:
            # Delete all nodes with TestModel label
            await session.run("MATCH (n:TestModel) DETACH DELETE n")
            # Delete all nodes with BatchTest label
            await session.run("MATCH (n:BatchTest) DETACH DELETE n")


class TestAsyncNeo4jIntegration:
    """Integration tests for AsyncNeo4jAdapter."""

    async def test_async_neo4j_single_node(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test AsyncNeo4jAdapter with a single node."""
        # Create test instance
        test_model = async_model_factory(id=44, name="test_async_neo4j", value=90.12)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncNeo4jAdapter)

        # Store in database
        await test_model.adapt_to_async(
            obj_key="async_neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )
        
        # Retrieve from database
        retrieved = await test_model.__class__.adapt_from_async(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.id = 44",
            },
            obj_key="async_neo4j",
            many=False,
        )

        # Verify data integrity
        assert retrieved.id == test_model.id
        assert retrieved.name == test_model.name
        assert retrieved.value == test_model.value

    async def test_async_neo4j_batch_operations(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test batch operations with AsyncNeo4jAdapter."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncNeo4jAdapter)

        # Create multiple test instances
        models = [
            model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            await model.adapt_to_async(
                obj_key="async_neo4j",
                url=neo4j_url,
                auth=neo4j_auth,
                label="BatchTest",
                merge_on="id",
            )

        # Retrieve all from database
        retrieved = await model_cls.adapt_from_async(
            {"url": neo4j_url, "auth": neo4j_auth, "label": "BatchTest"},
            obj_key="async_neo4j",
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

    async def test_async_neo4j_connection_error(self, async_model_factory):
        """Test handling of Neo4j connection errors."""
        test_model = async_model_factory(id=44, name="test_async_neo4j", value=90.12)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncNeo4jAdapter)

        # Test with invalid connection string
        with pytest.raises(ConnectionError):
            await test_model.adapt_to_async(
                obj_key="async_neo4j",
                url="neo4j://invalid:invalid@localhost:7687",
                label="TestModel",
                merge_on="id",
            )

    async def test_async_neo4j_resource_not_found(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test handling of resource not found errors."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncNeo4jAdapter)

        # Try to retrieve from non-existent node
        with pytest.raises(ResourceError):
            await model_cls.adapt_from_async(
                {
                    "url": neo4j_url,
                    "auth": neo4j_auth,
                    "label": "NonExistentLabel",
                    "where": "n.id = 999",
                },
                obj_key="async_neo4j",
                many=False,
            )

    async def test_async_neo4j_update_node(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test updating an existing node in Neo4j."""
        # Create test instance
        test_model = async_model_factory(id=99, name="original", value=100.0)

        # Register adapter
        test_model.__class__.register_async_adapter(AsyncNeo4jAdapter)

        # Store in database
        await test_model.adapt_to_async(
            obj_key="async_neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )

        # Create updated model with same ID
        updated_model = async_model_factory(id=99, name="updated", value=200.0)

        # Register adapter for updated model
        updated_model.__class__.register_async_adapter(AsyncNeo4jAdapter)

        # Update in database
        await updated_model.adapt_to_async(
            obj_key="async_neo4j",
            url=neo4j_url,
            auth=neo4j_auth,
            label="TestModel",
            merge_on="id",
        )

        # Retrieve from database
        retrieved = await test_model.__class__.adapt_from_async(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.id = 99",
            },
            obj_key="async_neo4j",
            many=False,
        )

        # Verify data was updated
        assert retrieved.id == 99
        assert retrieved.name == "updated"
        assert retrieved.value == 200.0

    async def test_async_neo4j_where_clause(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test filtering with Neo4j where clause."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncNeo4jAdapter)

        # Create multiple test instances with different values
        models = [
            model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 11)
        ]

        # Store batch in database
        for model in models:
            await model.adapt_to_async(
                obj_key="async_neo4j",
                url=neo4j_url,
                auth=neo4j_auth,
                label="TestModel",
                merge_on="id",
            )

        # Retrieve with where clause (value > 50 AND id >= 6 AND id <= 10)
        retrieved = await model_cls.adapt_from_async(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "TestModel",
                "where": "n.value > 50 AND n.id >= 6 AND n.id <= 10",
            },
            obj_key="async_neo4j",
            many=True,
        )

        # Verify filtered results
        assert len(retrieved) == 5  # IDs 6-10 have values > 50
        for model in retrieved:
            assert model.value > 50

    async def test_async_neo4j_empty_result_many(
        self, neo4j_url, neo4j_auth, async_model_factory, async_neo4j_cleanup
    ):
        """Test handling of empty result sets with many=True."""
        model_cls = async_model_factory(id=1, name="test", value=1.0).__class__

        # Register adapter
        model_cls.register_async_adapter(AsyncNeo4jAdapter)

        # Query for non-existent nodes with many=True
        result = await model_cls.adapt_from_async(
            {
                "url": neo4j_url,
                "auth": neo4j_auth,
                "label": "EmptyLabel",  # This label doesn't exist
            },
            obj_key="async_neo4j",
            many=True,
        )

        # Verify empty list is returned
        assert isinstance(result, list)
        assert len(result) == 0