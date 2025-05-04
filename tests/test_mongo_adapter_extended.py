"""
Extended tests for MongoDB adapter functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from pydantic import BaseModel

from pydapter.core import Adaptable
from pydapter.extras.mongo_ import MongoAdapter


@pytest.fixture
def mongo_model_factory():
    """Factory for creating test models with MongoDB adapter registered."""

    def create_model(**kw):
        class TestModel(Adaptable, BaseModel):
            id: int
            name: str
            value: float

        # Register the MongoDB adapter
        TestModel.register_adapter(MongoAdapter)
        return TestModel(**kw)

    return create_model


@pytest.fixture
def mongo_sample(mongo_model_factory):
    """Create a sample model instance."""
    return mongo_model_factory(id=1, name="test", value=42.5)


class TestMongoAdapterExtended:
    """Extended tests for MongoDB adapter functionality."""

    def test_mongo_client_helper(self):
        """Test the _client helper method."""
        # Mock the MongoClient
        with patch("pydapter.extras.mongo_.MongoClient") as mock_mongo_client:
            # Call the _client helper
            MongoAdapter._client("mongodb://localhost:27017")
            
            # Verify MongoClient was called with the URL
            mock_mongo_client.assert_called_once_with("mongodb://localhost:27017")

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_from_obj_with_filter(self, mock_mongo_client, mongo_sample):
        """Test conversion from MongoDB document to model with filter."""
        # Setup mock client, database, collection, and find
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock the find result
        mock_collection.find.return_value = [
            {"id": 1, "name": "test", "value": 42.5}
        ]
        
        # Test from_obj with filter
        model_cls = mongo_sample.__class__
        result = model_cls.adapt_from(
            {
                "url": "mongodb://localhost:27017",
                "db": "test_db",
                "collection": "test_collection",
                "filter": {"id": 1}
            }, 
            obj_key="mongo"
        )
        
        # Verify find was called with the filter
        mock_collection.find.assert_called_once_with({"id": 1})
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_from_obj_without_filter(self, mock_mongo_client, mongo_sample):
        """Test conversion from MongoDB document to model without filter."""
        # Setup mock client, database, collection, and find
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock the find result
        mock_collection.find.return_value = [
            {"id": 1, "name": "test", "value": 42.5}
        ]
        
        # Test from_obj without filter
        model_cls = mongo_sample.__class__
        result = model_cls.adapt_from(
            {
                "url": "mongodb://localhost:27017",
                "db": "test_db",
                "collection": "test_collection"
            }, 
            obj_key="mongo"
        )
        
        # Verify find was called with an empty filter
        mock_collection.find.assert_called_once_with({})
        
        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "test"
        assert result[0].value == 42.5

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_from_obj_single(self, mock_mongo_client, mongo_sample):
        """Test conversion from MongoDB document to model with many=False."""
        # Setup mock client, database, collection, and find
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock the find result
        mock_collection.find.return_value = [
            {"id": 1, "name": "test", "value": 42.5}
        ]
        
        # Test from_obj with many=False
        model_cls = mongo_sample.__class__
        result = model_cls.adapt_from(
            {
                "url": "mongodb://localhost:27017",
                "db": "test_db",
                "collection": "test_collection"
            }, 
            obj_key="mongo",
            many=False
        )
        
        # Verify the result is a single model, not a list
        assert not isinstance(result, list)
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42.5

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_to_obj_multiple_items(self, mock_mongo_client, mongo_model_factory):
        """Test conversion from multiple models to MongoDB documents."""
        # Create multiple models
        model1 = mongo_model_factory(id=1, name="test1", value=42.5)
        model2 = mongo_model_factory(id=2, name="test2", value=43.5)
        
        # Setup mock client, database, collection, and insert_many
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Directly test the adapter's to_obj method with multiple items
        MongoAdapter.to_obj(
            [model1, model2],
            url="mongodb://localhost:27017",
            db="test_db",
            collection="test_collection"
        )
        
        # Verify insert_many was called with the correct documents
        expected_docs = [
            {"id": 1, "name": "test1", "value": 42.5},
            {"id": 2, "name": "test2", "value": 43.5}
        ]
        mock_collection.insert_many.assert_called_once_with(expected_docs)

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_to_obj_with_single_item(self, mock_mongo_client, mongo_sample):
        """Test conversion from a single model to MongoDB document."""
        # Setup mock client, database, collection, and insert_many
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Test to_obj with a single item and many=False
        mongo_sample.adapt_to(
            obj_key="mongo", 
            url="mongodb://localhost:27017",
            db="test_db",
            collection="test_collection",
            many=False
        )
        
        # Verify insert_many was called with a list containing the single document
        expected_docs = [{"id": 1, "name": "test", "value": 42.5}]
        mock_collection.insert_many.assert_called_once_with(expected_docs)

    @patch("pydapter.extras.mongo_.MongoClient")
    def test_mongo_to_obj_with_custom_parameters(self, mock_mongo_client, mongo_sample):
        """Test conversion from model to MongoDB document with custom parameters."""
        # Setup mock client, database, collection, and insert_many
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Test to_obj with custom parameters
        mongo_sample.adapt_to(
            obj_key="mongo", 
            url="mongodb://user:pass@localhost:27017/admin",
            db="custom_db",
            collection="custom_collection"
        )
        
        # Verify the client was created with the custom URL
        mock_mongo_client.assert_called_once_with("mongodb://user:pass@localhost:27017/admin")
        
        # Verify the correct database and collection were accessed
        mock_mongo_client.return_value.__getitem__.assert_called_once_with("custom_db")
        mock_db.__getitem__.assert_called_once_with("custom_collection")