import tempfile
import uuid

import pytest

from pydapter import Adaptable
from pydapter.adapters import CsvAdapter, JsonAdapter, TomlAdapter
from pydapter.async_core import AsyncAdaptable


@pytest.fixture
def _ModelFactory():
    class Factory:
        def __call__(self, **kw):
            from pydantic import BaseModel

            class M(Adaptable, BaseModel):
                id: int
                name: str
                value: float

            M.register_adapter(JsonAdapter)
            M.register_adapter(CsvAdapter)
            M.register_adapter(TomlAdapter)
            return M(**kw)

    return Factory()


@pytest.fixture
def sample(_ModelFactory):  # pylint: disable=invalid-name
    return _ModelFactory(id=1, name="foo", value=42.5)


@pytest.fixture(scope="session")
def pg_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        # Convert the URL to use asyncpg instead of psycopg2
        url = pg.get_connection_url()  # postgresql://user:pass@host:port/db
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        yield url


@pytest.fixture(scope="session")
def qdrant_url():
    from testcontainers.qdrant import QdrantContainer

    with QdrantContainer("qdrant/qdrant:v1.8.1") as qc:
        yield f"http://{qc.get_container_host_ip()}:{qc.get_exposed_port(6333)}"


@pytest.fixture(scope="session")
def mongo_url():
    from testcontainers.mongodb import MongoDbContainer

    # Use MongoDB container with authentication
    with (
        MongoDbContainer("mongo:6.0")
        .with_env("MONGO_INITDB_ROOT_USERNAME", "test")
        .with_env("MONGO_INITDB_ROOT_PASSWORD", "test") as mongo
    ):
        yield f"mongodb://test:test@{mongo.get_container_host_ip()}:{mongo.get_exposed_port(27017)}"


@pytest.fixture
def async_model_factory():
    from pydantic import BaseModel

    from pydapter.extras.async_mongo_ import AsyncMongoAdapter
    from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
    from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

    class AsyncModel(AsyncAdaptable, BaseModel):
        id: int
        name: str
        value: float
        embedding: list[float] = [0.1, 0.2, 0.3, 0.4, 0.5]  # For vector DBs

    # Register async adapters
    AsyncModel.register_async_adapter(AsyncPostgresAdapter)
    AsyncModel.register_async_adapter(AsyncMongoAdapter)
    AsyncModel.register_async_adapter(AsyncQdrantAdapter)

    return AsyncModel


@pytest.fixture
def async_sample(async_model_factory):
    return async_model_factory(id=1, name="foo", value=42.5)
