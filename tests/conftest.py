import pytest
import uuid
import tempfile
from pydapter import Adaptable
from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter


class _ModelFactory:
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


@pytest.fixture
def sample(_ModelFactory):  # pylint: disable=invalid-name
    return _ModelFactory(id=1, name="foo", value=42.5)


@pytest.fixture(scope="session")
def pg_url():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()  # postgresql://user:pass@host:port/db


@pytest.fixture(scope="session")
def qdrant_url():
    from testcontainers.qdrant import QdrantContainer

    with QdrantContainer("qdrant/qdrant:v1.8.1") as qc:
        yield f"http://{qc.get_container_host_ip()}:{qc.get_exposed_port(6333)}"