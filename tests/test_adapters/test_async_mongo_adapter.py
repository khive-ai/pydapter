"""
Comprehensive tests for AsyncMongoAdapter functionality.

This test suite covers:
- Error path tests (missing parameters, invalid URIs, connection failures, validation errors)
- CRUD operations (insert, find, update, delete)
- Edge cases (ObjectId handling, nested documents, empty results)
- Integration tests with real MongoDB using testcontainers
"""

from unittest.mock import AsyncMock, patch

from pydantic import BaseModel
import pymongo
import pymongo.errors
import pytest
import pytest_asyncio

from pydapter.async_core import AsyncAdaptable
from pydapter.exceptions import (
    ConnectionError as AdapterConnectionError,
)
from pydapter.exceptions import (
    PydapterError,
    QueryError,
    ResourceError,
)
from pydapter.exceptions import ValidationError as AdapterValidationError
from pydapter.extras.async_mongo_ import AsyncMongoAdapter


def is_docker_available():
    """Check if Docker is available."""
    import subprocess

    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


# Skip integration tests if Docker is not available
integration_test = pytest.mark.skipif(
    not is_docker_available(), reason="Docker is not available"
)


@pytest.fixture
def async_mongo_model_factory():
    """Factory for creating test models with AsyncMongoAdapter registered."""

    def create_model(**kw):
        class TestModel(AsyncAdaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the async MongoDB adapter
        TestModel.register_async_adapter(AsyncMongoAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def async_mongo_sample(async_mongo_model_factory):
    """Create a sample model instance."""
    return async_mongo_model_factory(id=1, name="test", value=42.5)


@pytest_asyncio.fixture
async def mongo_cleanup(mongo_url):
    """Clean up MongoDB collections after tests."""
    yield

    # Cleanup after test
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(mongo_url)
    db = client["testdb"]
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)
    client.close()


class TestAsyncMongoAdapterProtocol:
    """Tests for AsyncMongoAdapter protocol compliance."""

    def test_async_mongo_adapter_protocol_compliance(self):
        """Test that AsyncMongoAdapter implements the Adapter protocol."""
        # Verify required attributes
        assert hasattr(AsyncMongoAdapter, "adapter_key")
        assert isinstance(AsyncMongoAdapter.adapter_key, str)
        assert AsyncMongoAdapter.adapter_key == "async_mongo"

        # Verify backward compatibility
        assert hasattr(AsyncMongoAdapter, "obj_key")
        assert AsyncMongoAdapter.obj_key == "async_mongo"

        # Verify method signatures
        assert hasattr(AsyncMongoAdapter, "from_obj")
        assert hasattr(AsyncMongoAdapter, "to_obj")

        # Verify the methods can be called as classmethods
        assert callable(AsyncMongoAdapter.from_obj)
        assert callable(AsyncMongoAdapter.to_obj)


class TestAsyncMongoAdapterErrorHandling:
    """Tests for AsyncMongoAdapter error handling."""

    @pytest.mark.asyncio
    async def test_async_mongo_missing_collection(self, async_mongo_sample):
        """Test error when collection parameter is empty."""
        with pytest.raises(AdapterValidationError, match="collection"):
            await AsyncMongoAdapter.to_obj(
                async_mongo_sample,
                url="mongodb://localhost:27017",
                db="testdb",
                collection="",  # Empty collection
            )

    @pytest.mark.asyncio
    async def test_async_mongo_missing_uri(self, async_mongo_sample):
        """Test error when URI parameter is empty."""
        with pytest.raises(AdapterValidationError, match="url"):
            await AsyncMongoAdapter.to_obj(
                async_mongo_sample,
                url="",  # Empty URL
                db="testdb",
                collection="test_coll",
            )

    @pytest.mark.asyncio
    async def test_async_mongo_missing_db(self, async_mongo_sample):
        """Test error when database parameter is empty."""
        with pytest.raises(AdapterValidationError, match="db"):
            await AsyncMongoAdapter.to_obj(
                async_mongo_sample,
                url="mongodb://localhost:27017",
                db="",  # Empty db
                collection="test_coll",
            )

    @pytest.mark.asyncio
    async def test_async_mongo_invalid_uri(self):
        """Test error when MongoDB URI is invalid."""

        class TestModel(BaseModel):
            name: str

        with pytest.raises(AdapterConnectionError, match="Invalid MongoDB connection"):
            await AsyncMongoAdapter.to_obj(
                TestModel(name="test"),
                url="invalid://not-a-mongo-uri",
                db="testdb",
                collection="test_coll",
            )

    @pytest.mark.asyncio
    async def test_async_mongo_connection_error(self):
        """Test handling of connection failure."""

        class TestModel(BaseModel):
            name: str

        # Use invalid host/port to trigger connection timeout
        with pytest.raises(AdapterConnectionError, match="server selection timeout"):
            await AsyncMongoAdapter.to_obj(
                TestModel(name="test"),
                url="mongodb://invalid:invalid@localhost:27017",
                db="testdb",
                collection="test_coll",
            )

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_validation_error(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test Pydantic validation failure during conversion."""

        class StrictModel(BaseModel):
            id: int
            name: str
            value: float
            required_field: str  # This field will be missing from MongoDB docs

        # Insert document missing required_field
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(mongo_url)
        db = client["testdb"]
        collection = db["validation_coll"]
        await collection.insert_one({"id": 1, "name": "test", "value": 42.5})
        client.close()

        # Try to retrieve with strict model (should fail validation)
        with pytest.raises(AdapterValidationError):
            await AsyncMongoAdapter.from_obj(
                StrictModel,
                {
                    "url": mongo_url,
                    "db": "testdb",
                    "collection": "validation_coll",
                    "filter": {"id": 1},
                },
                many=False,
            )

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_empty_results_many_true(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test empty query results with many=True returns empty list."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Query non-existent data with many=True (should return empty list)
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "empty_coll",
                "filter": {"id": 999},
            },
            many=True,
        )

        # Should return empty list, not raise error
        assert result == []

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_empty_results_many_false(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test empty query results with many=False raises ResourceError."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Query non-existent data with many=False (should raise ResourceError)
        with pytest.raises(ResourceError, match="No documents found"):
            await AsyncMongoAdapter.from_obj(
                model_cls,
                {
                    "url": mongo_url,
                    "db": "testdb",
                    "collection": "empty_coll",
                    "filter": {"id": 999},
                },
                many=False,
            )

    @pytest.mark.asyncio
    async def test_async_mongo_invalid_filter_type(self):
        """Test validation error when filter is not a dictionary."""

        class TestModel(BaseModel):
            name: str

        # Mock the client and connection to focus on filter validation
        with patch.object(AsyncMongoAdapter, "_client"):
            with patch.object(AsyncMongoAdapter, "_validate_connection") as mock_validate:
                mock_validate.return_value = None

                with pytest.raises(AdapterValidationError, match="Filter must be a dictionary"):
                    await AsyncMongoAdapter.from_obj(
                        TestModel,
                        {
                            "url": "mongodb://localhost:27017",
                            "db": "testdb",
                            "collection": "test_coll",
                            "filter": "invalid_filter",  # Should be dict
                        },
                        many=False,
                    )


class TestAsyncMongoAdapterCRUDOperations:
    """Tests for AsyncMongoAdapter CRUD operations."""

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_insert_single(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test single document insert."""
        model = async_mongo_model_factory(id=1, name="single_insert", value=100.0)

        # Insert single document
        result = await AsyncMongoAdapter.to_obj(
            model,
            url=mongo_url,
            db="testdb",
            collection="single_coll",
            many=False,
        )

        # Verify insert result
        assert result is not None
        assert result["inserted_count"] == 1

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_insert_batch(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test batch insert (many=True)."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Create multiple documents
        models = [model_cls(id=i, name=f"batch_{i}", value=i * 1.5) for i in range(1, 6)]

        # Insert batch
        result = await AsyncMongoAdapter.to_obj(
            models,
            url=mongo_url,
            db="testdb",
            collection="batch_coll",
            many=True,
        )

        # Verify batch insert result
        assert result is not None
        assert result["inserted_count"] == 5

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_find_basic(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test basic query without filter."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert test data
        models = [model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 4)]
        await AsyncMongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="find_coll", many=True
        )

        # Query all documents
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {"url": mongo_url, "db": "testdb", "collection": "find_coll"},
            many=True,
        )

        # Verify results
        assert len(result) == 3
        assert all(isinstance(doc, model_cls) for doc in result)

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_find_with_filter(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test query with filters."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert test data
        models = [model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 11)]
        await AsyncMongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="filter_coll", many=True
        )

        # Query with filter (value > 50)
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "filter_coll",
                "filter": {"value": {"$gt": 50}},
            },
            many=True,
        )

        # Verify filtered results
        assert len(result) == 5  # IDs 6-10 have values > 50
        assert all(doc.value > 50 for doc in result)

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_find_single(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test finding single document with many=False."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert single document
        model = model_cls(id=42, name="single_find", value=99.5)
        await AsyncMongoAdapter.to_obj(
            model, url=mongo_url, db="testdb", collection="single_find_coll", many=False
        )

        # Query single document
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "single_find_coll",
                "filter": {"id": 42},
            },
            many=False,
        )

        # Verify single result
        assert isinstance(result, model_cls)
        assert result.id == 42
        assert result.name == "single_find"
        assert result.value == 99.5

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_update(self, mongo_url, async_mongo_model_factory, mongo_cleanup):
        """Test update operation."""
        from motor.motor_asyncio import AsyncIOMotorClient

        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert initial document
        model = model_cls(id=1, name="original", value=10.0)
        await AsyncMongoAdapter.to_obj(
            model, url=mongo_url, db="testdb", collection="update_coll", many=False
        )

        # Update using Motor directly (AsyncMongoAdapter doesn't have update method)
        client = AsyncIOMotorClient(mongo_url)
        db = client["testdb"]
        collection = db["update_coll"]
        await collection.update_one({"id": 1}, {"$set": {"name": "updated", "value": 20.0}})
        client.close()

        # Verify update
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {"url": mongo_url, "db": "testdb", "collection": "update_coll", "filter": {"id": 1}},
            many=False,
        )

        assert result.name == "updated"
        assert result.value == 20.0

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_delete(self, mongo_url, async_mongo_model_factory, mongo_cleanup):
        """Test delete operation."""
        from motor.motor_asyncio import AsyncIOMotorClient

        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert documents
        models = [model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 4)]
        await AsyncMongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="delete_coll", many=True
        )

        # Delete one document using Motor directly
        client = AsyncIOMotorClient(mongo_url)
        db = client["testdb"]
        collection = db["delete_coll"]
        delete_result = await collection.delete_one({"id": 2})
        client.close()

        # Verify deletion
        assert delete_result.deleted_count == 1

        # Query remaining documents
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {"url": mongo_url, "db": "testdb", "collection": "delete_coll"},
            many=True,
        )

        assert len(result) == 2
        assert all(doc.id != 2 for doc in result)


class TestAsyncMongoAdapterEdgeCases:
    """Tests for AsyncMongoAdapter edge cases."""

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_objectid_handling(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test handling of MongoDB ObjectId in _id field."""

        class DocWithObjectId(AsyncAdaptable, BaseModel):
            id: int
            name: str
            # MongoDB adds _id automatically, we test it doesn't break parsing

        DocWithObjectId.register_async_adapter(AsyncMongoAdapter)

        # Insert document
        doc = DocWithObjectId(id=1, name="with_objectid")
        await AsyncMongoAdapter.to_obj(
            doc, url=mongo_url, db="testdb", collection="objectid_coll", many=False
        )

        # Retrieve document (MongoDB will have _id field)
        result = await AsyncMongoAdapter.from_obj(
            DocWithObjectId,
            {"url": mongo_url, "db": "testdb", "collection": "objectid_coll", "filter": {"id": 1}},
            many=False,
        )

        # Verify document was retrieved despite _id field
        assert result.id == 1
        assert result.name == "with_objectid"

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_nested_documents(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test nested Pydantic models."""

        class Address(BaseModel):
            street: str
            city: str
            zip_code: str

        class Person(AsyncAdaptable, BaseModel):
            id: int
            name: str
            address: Address

        Person.register_async_adapter(AsyncMongoAdapter)

        # Create nested document
        person = Person(
            id=1, name="John Doe", address=Address(street="123 Main St", city="NYC", zip_code="10001")
        )

        # Insert nested document
        await AsyncMongoAdapter.to_obj(
            person, url=mongo_url, db="testdb", collection="nested_coll", many=False
        )

        # Retrieve nested document
        result = await AsyncMongoAdapter.from_obj(
            Person,
            {"url": mongo_url, "db": "testdb", "collection": "nested_coll", "filter": {"id": 1}},
            many=False,
        )

        # Verify nested structure
        assert result.id == 1
        assert result.name == "John Doe"
        assert result.address.street == "123 Main St"
        assert result.address.city == "NYC"
        assert result.address.zip_code == "10001"

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_empty_payload(self, mongo_url, async_mongo_model_factory):
        """Test inserting empty payload returns None."""
        # Insert empty list
        result = await AsyncMongoAdapter.to_obj(
            [],  # Empty list
            url=mongo_url,
            db="testdb",
            collection="empty_payload_coll",
            many=True,
        )

        # Should return None for empty payload
        assert result is None

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_filter_none(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test that None filter is treated as empty filter (matches all)."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert test data
        models = [model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 4)]
        await AsyncMongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="filter_none_coll", many=True
        )

        # Query with None filter (should match all)
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "filter_none_coll",
                "filter": None,  # None should be treated as {}
            },
            many=True,
        )

        # Verify all documents returned
        assert len(result) == 3

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_complex_filter(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test complex MongoDB query filters."""
        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Insert test data
        models = [model_cls(id=i, name=f"test_{i}", value=i * 10.0) for i in range(1, 11)]
        await AsyncMongoAdapter.to_obj(
            models, url=mongo_url, db="testdb", collection="complex_filter_coll", many=True
        )

        # Query with complex filter ($and, $or, $in)
        result = await AsyncMongoAdapter.from_obj(
            model_cls,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "complex_filter_coll",
                "filter": {"$and": [{"value": {"$gte": 30}}, {"value": {"$lte": 70}}]},
            },
            many=True,
        )

        # Verify filtered results (values 30-70: IDs 3-7)
        assert len(result) == 5
        assert all(30 <= doc.value <= 70 for doc in result)


class TestAsyncMongoAdapterIntegration:
    """Additional integration tests for real-world scenarios."""

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_roundtrip(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test complete roundtrip: insert and retrieve."""
        model = async_mongo_model_factory(id=42, name="roundtrip", value=99.99)

        # Insert
        await AsyncMongoAdapter.to_obj(
            model, url=mongo_url, db="testdb", collection="roundtrip_coll", many=False
        )

        # Retrieve
        result = await AsyncMongoAdapter.from_obj(
            model.__class__,
            {
                "url": mongo_url,
                "db": "testdb",
                "collection": "roundtrip_coll",
                "filter": {"id": 42},
            },
            many=False,
        )

        # Verify data integrity
        assert result.id == model.id
        assert result.name == model.name
        assert result.value == model.value

    @pytest.mark.asyncio
    @integration_test
    async def test_async_mongo_concurrent_operations(
        self, mongo_url, async_mongo_model_factory, mongo_cleanup
    ):
        """Test concurrent async operations."""
        import asyncio

        model_cls = async_mongo_model_factory(id=1, name="test", value=1.0).__class__

        # Create multiple insert tasks
        async def insert_doc(doc_id):
            model = model_cls(id=doc_id, name=f"concurrent_{doc_id}", value=doc_id * 5.0)
            return await AsyncMongoAdapter.to_obj(
                model, url=mongo_url, db="testdb", collection="concurrent_coll", many=False
            )

        # Run concurrent inserts
        tasks = [insert_doc(i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)

        # Verify all inserts succeeded
        assert all(r["inserted_count"] == 1 for r in results)

        # Retrieve all documents
        all_docs = await AsyncMongoAdapter.from_obj(
            model_cls,
            {"url": mongo_url, "db": "testdb", "collection": "concurrent_coll"},
            many=True,
        )

        # Verify all documents exist
        assert len(all_docs) == 5


class TestAsyncMongoAdapterCoverageGaps:
    """Tests targeting uncovered error paths for 90%+ coverage."""

    @pytest.mark.asyncio
    async def test_async_mongo_client_creation_generic_error(self):
        """Test generic exception during client creation."""

        class TestModel(BaseModel):
            name: str

        # Mock AsyncIOMotorClient to raise a generic exception
        with patch("pydapter.extras.async_mongo_.AsyncIOMotorClient") as mock_client:
            mock_client.side_effect = RuntimeError("Unexpected client error")

            with pytest.raises(AdapterConnectionError, match="Failed to create MongoDB client"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_validate_connection_operation_failure_auth(self):
        """Test connection validation with authentication failure."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client

            # Simulate auth failure
            mock_client.admin.command.side_effect = pymongo.errors.OperationFailure(
                "auth failed: invalid credentials"
            )

            with pytest.raises(AdapterConnectionError, match="authentication failed"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://invalid:invalid@localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_validate_connection_operation_failure_other(self):
        """Test connection validation with non-auth operation failure."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client

            # Simulate non-auth operation failure
            mock_client.admin.command.side_effect = pymongo.errors.OperationFailure(
                "command failed"
            )

            with pytest.raises(QueryError, match="MongoDB operation failure"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_validate_connection_generic_error(self):
        """Test connection validation with generic exception."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client

            # Simulate generic error during connection validation
            mock_client.admin.command.side_effect = RuntimeError("Unexpected connection error")

            with pytest.raises(AdapterConnectionError, match="Failed to connect to MongoDB"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_validate_params_generic_error_from_obj(self):
        """Test unexpected error in parameter validation during from_obj."""

        class TestModel(BaseModel):
            name: str

        # Mock _validate_params to raise unexpected error
        with patch.object(
            AsyncMongoAdapter, "_validate_params"
        ) as mock_validate:
            mock_validate.side_effect = RuntimeError("Unexpected validation error")

            with pytest.raises(PydapterError):
                await AsyncMongoAdapter.from_obj(
                    TestModel,
                    {
                        "url": "mongodb://localhost:27017",
                        "db": "testdb",
                        "collection": "test_coll",
                    },
                    many=False,
                )

    @pytest.mark.asyncio
    async def test_async_mongo_validate_filter_generic_error(self):
        """Test unexpected error in filter validation."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            with patch.object(
                AsyncMongoAdapter, "_validate_filter"
            ) as mock_validate_filter:
                mock_validate_filter.side_effect = RuntimeError("Unexpected filter error")

                with pytest.raises(PydapterError):
                    await AsyncMongoAdapter.from_obj(
                        TestModel,
                        {
                            "url": "mongodb://localhost:27017",
                            "db": "testdb",
                            "collection": "test_coll",
                            "filter": {"id": 1},
                        },
                        many=False,
                    )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_find_authorization_error(self):
        """Test authorization error during find operation."""
        from unittest.mock import Mock

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection find to raise authorization error
            # Create an async function that raises the error
            async def raise_auth_error(*args, **kwargs):
                raise pymongo.errors.OperationFailure(
                    "not authorized on testdb to execute command"
                )

            # Use regular Mock for cursor since .find() returns synchronously
            mock_cursor = Mock()
            mock_cursor.to_list = raise_auth_error

            mock_collection = AsyncMock()
            # Make find() return the cursor synchronously (not a coroutine)
            mock_collection.find = Mock(return_value=mock_cursor)
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(AdapterConnectionError, match="Not authorized to access"):
                await AsyncMongoAdapter.from_obj(
                    TestModel,
                    {
                        "url": "mongodb://localhost:27017",
                        "db": "testdb",
                        "collection": "test_coll",
                        "filter": {"id": 1},
                    },
                    many=False,
                )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_find_operation_failure(self):
        """Test operation failure during find operation."""
        from unittest.mock import Mock

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection find to raise operation failure
            # Create an async function that raises the error
            async def raise_operation_failure(*args, **kwargs):
                raise pymongo.errors.OperationFailure("query failed")

            # Use regular Mock for cursor since .find() returns synchronously
            mock_cursor = Mock()
            mock_cursor.to_list = raise_operation_failure

            mock_collection = AsyncMock()
            # Make find() return the cursor synchronously (not a coroutine)
            mock_collection.find = Mock(return_value=mock_cursor)
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(QueryError, match="MongoDB query error"):
                await AsyncMongoAdapter.from_obj(
                    TestModel,
                    {
                        "url": "mongodb://localhost:27017",
                        "db": "testdb",
                        "collection": "test_coll",
                        "filter": {"id": 1},
                    },
                    many=False,
                )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_find_generic_error(self):
        """Test generic error during find operation."""
        from unittest.mock import Mock

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection find to raise generic error
            # Create an async function that raises the error
            async def raise_generic_error(*args, **kwargs):
                raise RuntimeError("Unexpected find error")

            # Use regular Mock for cursor since .find() returns synchronously
            mock_cursor = Mock()
            mock_cursor.to_list = raise_generic_error

            mock_collection = AsyncMock()
            # Make find() return the cursor synchronously (not a coroutine)
            mock_collection.find = Mock(return_value=mock_cursor)
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(QueryError, match="Error executing MongoDB query"):
                await AsyncMongoAdapter.from_obj(
                    TestModel,
                    {
                        "url": "mongodb://localhost:27017",
                        "db": "testdb",
                        "collection": "test_coll",
                        "filter": {"id": 1},
                    },
                    many=False,
                )

    @pytest.mark.asyncio
    async def test_async_mongo_prepare_payload_error(self):
        """Test error during payload preparation."""

        class TestModel(BaseModel):
            name: str

        # Mock dispatch_adapt_meth to raise error
        with patch("pydapter.extras.async_mongo_.dispatch_adapt_meth") as mock_dispatch:
            mock_dispatch.side_effect = RuntimeError("Serialization error")

            with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
                mock_client = AsyncMock()
                mock_client_method.return_value = mock_client
                mock_client.admin.command = AsyncMock()  # Successful connection

                with pytest.raises(PydapterError):
                    await AsyncMongoAdapter.to_obj(
                        TestModel(name="test"),
                        url="mongodb://localhost:27017",
                        db="testdb",
                        collection="test_coll",
                    )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_insert_bulk_write_error(self):
        """Test bulk write error during insert."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection insert_many to raise BulkWriteError
            mock_collection = AsyncMock()

            # Create an async function that raises the error
            async def raise_bulk_write_error(*args, **kwargs):
                raise pymongo.errors.BulkWriteError(
                    {"writeErrors": [{"index": 0, "code": 11000, "errmsg": "duplicate key"}]}
                )

            mock_collection.insert_many = raise_bulk_write_error
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(QueryError, match="MongoDB bulk write error"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_insert_authorization_error(self):
        """Test authorization error during insert."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection insert_many to raise authorization error
            mock_collection = AsyncMock()

            # Create an async function that raises the error
            async def raise_auth_error(*args, **kwargs):
                raise pymongo.errors.OperationFailure(
                    "not authorized on testdb to execute command"
                )

            mock_collection.insert_many = raise_auth_error
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(AdapterConnectionError, match="Not authorized to write"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_insert_operation_failure(self):
        """Test operation failure during insert."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection insert_many to raise operation failure
            mock_collection = AsyncMock()

            # Create an async function that raises the error
            async def raise_operation_failure(*args, **kwargs):
                raise pymongo.errors.OperationFailure("insert failed")

            mock_collection.insert_many = raise_operation_failure
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(QueryError, match="MongoDB operation failure"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_execute_insert_generic_error(self):
        """Test generic error during insert."""

        class TestModel(BaseModel):
            name: str

        with patch.object(AsyncMongoAdapter, "_client") as mock_client_method:
            mock_client = AsyncMock()
            mock_client_method.return_value = mock_client
            mock_client.admin.command = AsyncMock()  # Successful connection

            # Mock collection insert_many to raise generic error
            mock_collection = AsyncMock()

            # Create an async function that raises the error
            async def raise_generic_error(*args, **kwargs):
                raise RuntimeError("Unexpected insert error")

            mock_collection.insert_many = raise_generic_error
            mock_client.__getitem__.return_value.__getitem__.return_value = mock_collection

            with pytest.raises(QueryError, match="Error inserting documents"):
                await AsyncMongoAdapter.to_obj(
                    TestModel(name="test"),
                    url="mongodb://localhost:27017",
                    db="testdb",
                    collection="test_coll",
                )

    @pytest.mark.asyncio
    async def test_async_mongo_from_obj_unexpected_error(self):
        """Test unexpected error handling in from_obj."""

        class TestModel(BaseModel):
            name: str

        # Mock client creation to raise unexpected error AFTER validation
        with patch.object(AsyncMongoAdapter, "_validate_params"):
            with patch.object(AsyncMongoAdapter, "_client") as mock_client:
                mock_client.side_effect = TypeError("Completely unexpected error")

                with pytest.raises(PydapterError):
                    await AsyncMongoAdapter.from_obj(
                        TestModel,
                        {
                            "url": "mongodb://localhost:27017",
                            "db": "testdb",
                            "collection": "test_coll",
                        },
                        many=False,
                    )

    @pytest.mark.asyncio
    async def test_async_mongo_to_obj_unexpected_error(self):
        """Test unexpected error handling in to_obj."""

        class TestModel(BaseModel):
            name: str

        # Mock client creation to raise unexpected error AFTER validation
        with patch.object(AsyncMongoAdapter, "_validate_params"):
            with patch.object(AsyncMongoAdapter, "_client") as mock_client:
                mock_client.side_effect = TypeError("Completely unexpected error")

                with pytest.raises(PydapterError):
                    await AsyncMongoAdapter.to_obj(
                        TestModel(name="test"),
                        url="mongodb://localhost:27017",
                        db="testdb",
                        collection="test_coll",
                    )
