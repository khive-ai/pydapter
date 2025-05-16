"""
Tests for SQL migration adapters.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, String, MetaData, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base

from pydapter.migrations.sql import AlembicMigrationAdapter, AsyncAlembicMigrationAdapter


class TestAlembicMigrationAdapter:
    """Test the AlembicMigrationAdapter class."""
    
    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for migrations
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test SQLite database
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.connection_string = f"sqlite:///{self.db_path}"
        
        # Create a test model
        self.Base = declarative_base()
        
        class User(self.Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))
        
        self.User = User
        self.models_module = MagicMock()
        self.models_module.__name__ = "test_models"
        self.models_module.Base = self.Base
    
    def teardown_method(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test initialization of the adapter."""
        adapter = AlembicMigrationAdapter(self.connection_string, self.models_module)
        
        assert adapter.connection_string == self.connection_string
        assert adapter.models_module == self.models_module
        assert adapter._initialized is False
        assert adapter._migrations_dir is None
        assert adapter.engine is not None
    
    @patch("alembic.command.init")
    def test_init_migrations(self, mock_init):
        """Test initializing migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        AlembicMigrationAdapter.init_migrations(
            migrations_dir,
            connection_string=self.connection_string,
            models_module=self.models_module
        )
        
        # Check that the directory was created
        assert os.path.exists(migrations_dir)
        
        # Check that Alembic was initialized
        mock_init.assert_called_once()
    
    @patch("alembic.command.revision")
    def test_create_migration(self, mock_revision):
        """Test creating a migration."""
        # Set up the mock
        mock_revision.return_value = MagicMock(revision="abc123")
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Create a migration
        revision = AlembicMigrationAdapter.create_migration(
            "Test migration",
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the migration was created
        assert revision == "abc123"
        mock_revision.assert_called_once()
    
    @patch("alembic.command.upgrade")
    def test_upgrade(self, mock_upgrade):
        """Test upgrading migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Upgrade migrations
        AlembicMigrationAdapter.upgrade(
            "head",
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the upgrade was called
        mock_upgrade.assert_called_once()
    
    @patch("alembic.command.downgrade")
    def test_downgrade(self, mock_downgrade):
        """Test downgrading migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Downgrade migrations
        AlembicMigrationAdapter.downgrade(
            "base",
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the downgrade was called
        mock_downgrade.assert_called_once()
    
    @patch("alembic.script.ScriptDirectory.from_config")
    def test_get_current_revision(self, mock_script_directory):
        """Test getting the current revision."""
        # Set up the mock
        mock_script = MagicMock()
        mock_script.get_current_head.return_value = "abc123"
        mock_script_directory.return_value = mock_script
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Get the current revision
        revision = AlembicMigrationAdapter.get_current_revision(
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the current revision was returned
        assert revision == "abc123"
    
    @patch("alembic.script.ScriptDirectory.from_config")
    def test_get_migration_history(self, mock_script_directory):
        """Test getting the migration history."""
        # Set up the mock
        mock_script = MagicMock()
        mock_revision = MagicMock()
        mock_revision.revision = "abc123"
        mock_revision.down_revision = None
        mock_revision.message = "Test migration"
        mock_revision.created_date = None
        mock_script.walk_revisions.return_value = [mock_revision]
        mock_script_directory.return_value = mock_script
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Get the migration history
        history = AlembicMigrationAdapter.get_migration_history(
            directory=migrations_dir
        )
        
        # Check that the migration history was returned
        assert len(history) == 1
        assert history[0]["revision"] == "abc123"
        assert history[0]["down_revision"] is None
        assert history[0]["message"] == "Test migration"
        assert history[0]["created_date"] is None


class TestAsyncAlembicMigrationAdapter:
    """Test the AsyncAlembicMigrationAdapter class."""
    
    def setup_method(self):
        """Set up the test environment."""
        # Create a temporary directory for migrations
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test SQLite database
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.connection_string = f"sqlite+aiosqlite:///{self.db_path}"
        
        # Create a test model
        self.Base = declarative_base()
        
        class User(self.Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))
        
        self.User = User
        self.models_module = MagicMock()
        self.models_module.__name__ = "test_models"
        self.models_module.Base = self.Base
    
    def teardown_method(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test initialization of the adapter."""
        adapter = AsyncAlembicMigrationAdapter(self.connection_string, self.models_module)
        
        assert adapter.connection_string == self.connection_string
        assert adapter.models_module == self.models_module
        assert adapter._initialized is False
        assert adapter._migrations_dir is None
        assert adapter.engine is not None
    
    @pytest.mark.asyncio
    @patch("alembic.command.init")
    async def test_init_migrations(self, mock_init):
        """Test initializing migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        await AsyncAlembicMigrationAdapter.init_migrations(
            migrations_dir,
            connection_string=self.connection_string,
            models_module=self.models_module
        )
        
        # Check that the directory was created
        assert os.path.exists(migrations_dir)
        
        # Check that Alembic was initialized
        mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(AsyncAlembicMigrationAdapter, "_create_migration_sync")
    async def test_create_migration(self, mock_create_migration_sync):
        """Test creating a migration."""
        # Set up the mock
        mock_create_migration_sync.return_value = "abc123"
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Create a migration without autogeneration
        revision = await AsyncAlembicMigrationAdapter.create_migration(
            "Test migration",
            autogenerate=False,
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the migration was created
        assert revision == "abc123"
        mock_create_migration_sync.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(AsyncAlembicMigrationAdapter, "_upgrade_sync")
    async def test_upgrade(self, mock_upgrade_sync):
        """Test upgrading migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Upgrade migrations
        await AsyncAlembicMigrationAdapter.upgrade(
            "head",
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the upgrade was called
        mock_upgrade_sync.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(AsyncAlembicMigrationAdapter, "_downgrade_sync")
    async def test_downgrade(self, mock_downgrade_sync):
        """Test downgrading migrations."""
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Downgrade migrations
        await AsyncAlembicMigrationAdapter.downgrade(
            "base",
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the downgrade was called
        mock_downgrade_sync.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(AsyncAlembicMigrationAdapter, "_get_current_revision_sync")
    async def test_get_current_revision(self, mock_get_current_revision_sync):
        """Test getting the current revision."""
        # Set up the mock
        mock_get_current_revision_sync.return_value = "abc123"
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Get the current revision
        revision = await AsyncAlembicMigrationAdapter.get_current_revision(
            directory=migrations_dir,
            connection_string=self.connection_string
        )
        
        # Check that the current revision was returned
        assert revision == "abc123"
    
    @pytest.mark.asyncio
    @patch("alembic.script.ScriptDirectory.from_config")
    async def test_get_migration_history(self, mock_script_directory):
        """Test getting the migration history."""
        # Set up the mock
        mock_script = MagicMock()
        mock_revision = MagicMock()
        mock_revision.revision = "abc123"
        mock_revision.down_revision = None
        mock_revision.message = "Test migration"
        mock_revision.created_date = None
        mock_script.walk_revisions.return_value = [mock_revision]
        mock_script_directory.return_value = mock_script
        
        # Initialize migrations
        migrations_dir = os.path.join(self.temp_dir, "migrations")
        os.makedirs(migrations_dir, exist_ok=True)
        
        # Create a fake alembic.ini file
        with open(os.path.join(migrations_dir, "alembic.ini"), "w") as f:
            f.write("[alembic]\n")
            f.write("script_location = migrations\n")
        
        # Get the migration history
        history = await AsyncAlembicMigrationAdapter.get_migration_history(
            directory=migrations_dir
        )
        
        # Check that the migration history was returned
        assert len(history) == 1
        assert history[0]["revision"] == "abc123"
        assert history[0]["down_revision"] is None
        assert history[0]["message"] == "Test migration"
        assert history[0]["created_date"] is None