"""Tests for credential redaction in BaseError and related helpers.

Covers H2 (credential leak through exception strings) and M11 (ConfigurationError
leaks full config dict) from the EMPACO consolidation findings.
"""

from __future__ import annotations

from pydapter.exceptions import ConfigurationError
from pydapter.exceptions import ConnectionError as AdapterConnectionError  # noqa: A004
from pydapter.types import BaseError, _redact_details, _redact_url

# ---------------------------------------------------------------------------
# _redact_url unit tests
# ---------------------------------------------------------------------------


class TestRedactUrl:
    """Unit tests for the _redact_url helper."""

    def test_postgresql_password_replaced(self):
        url = "postgresql://alice:s3cr3t@db.example.com:5432/mydb"
        result = _redact_url(url)
        assert "s3cr3t" not in result
        assert "***" in result
        assert "alice" in result
        assert "db.example.com" in result

    def test_postgresql_asyncpg_driver_scheme(self):
        """Driver-specific scheme must be handled (was broken with old regex)."""
        url = "postgresql+asyncpg://user:hunter2@localhost:5432/app"
        result = _redact_url(url)
        assert "hunter2" not in result
        assert "***" in result

    def test_mongodb_srv_scheme(self):
        """mongodb+srv:// must be handled (was broken with old regex)."""
        url = "mongodb+srv://admin:Pa$$w0rd@cluster0.example.mongodb.net/prod"
        result = _redact_url(url)
        assert "Pa$$w0rd" not in result
        assert "***" in result

    def test_redis_url(self):
        url = "redis://:mypassword@cache.example.com:6379/0"
        result = _redact_url(url)
        assert "mypassword" not in result

    def test_no_password_url_unchanged(self):
        url = "postgresql://localhost:5432/mydb"
        assert _redact_url(url) == url

    def test_non_credential_scheme_unchanged(self):
        url = "s3://my-bucket/prefix"
        assert _redact_url(url) == url

    def test_plain_string_unchanged(self):
        assert _redact_url("just a plain string") == "just a plain string"

    def test_non_string_passthrough(self):
        # Non-strings should be returned as-is (type guard in caller).
        assert _redact_url(None) is None  # type: ignore[arg-type]

    def test_neo4j_scheme(self):
        url = "neo4j+s://neo4j:bolt_pass@graph.example.com:7687"
        result = _redact_url(url)
        assert "bolt_pass" not in result
        assert "***" in result


# ---------------------------------------------------------------------------
# _redact_details unit tests
# ---------------------------------------------------------------------------


class TestRedactDetails:
    """Unit tests for the _redact_details helper."""

    def test_sensitive_key_url_redacted(self):
        details = {"url": "postgresql://user:pw@host/db"}
        result = _redact_details(details)
        assert "pw" not in result["url"]

    def test_sensitive_key_password_redacted(self):
        details = {"password": "topsecret"}
        result = _redact_details(details)
        assert result["password"] == "***"

    def test_sensitive_key_token_redacted(self):
        details = {"token": "eyJhbGciOiJIUzI1NiJ9.payload.sig"}
        result = _redact_details(details)
        assert result["token"] == "***"

    def test_sensitive_key_api_key_redacted(self):
        details = {"api_key": "sk-abc123"}
        result = _redact_details(details)
        assert result["api_key"] == "***"

    def test_sensitive_key_dsn_redacted(self):
        details = {"dsn": "postgresql://user:pw@host/db"}
        result = _redact_details(details)
        # DSN key is sensitive, so value should be '***' (not URL-parsed since key matches).
        assert "pw" not in str(result["dsn"])

    def test_non_sensitive_key_url_in_value_still_sanitized(self):
        """A non-sensitive key whose value contains '://' should be URL-sanitised."""
        details = {"connection": "mongodb://admin:secret@localhost/db"}
        result = _redact_details(details)
        assert "secret" not in str(result["connection"])

    def test_long_value_truncated(self):
        details = {"data": "x" * 600}
        result = _redact_details(details)
        assert len(result["data"]) <= 515  # 500 + len("... (truncated)")
        assert "truncated" in result["data"]

    def test_non_sensitive_short_value_unchanged(self):
        details = {"adapter": "postgres", "category": "connection"}
        result = _redact_details(details)
        assert result == details

    def test_config_dict_with_sensitive_keys_fully_redacted(self):
        """A config dict stored under a sensitive key must have all values hidden."""
        details = {"password": {"host": "db", "user": "alice", "password": "pw"}}
        result = _redact_details(details)
        # The whole dict value must be hidden because key is 'password'.
        assert "pw" not in str(result["password"])

    def test_empty_details_unchanged(self):
        assert _redact_details({}) == {}


# ---------------------------------------------------------------------------
# BaseError integration tests
# ---------------------------------------------------------------------------


class TestBaseErrorRedaction:
    """Integration tests: BaseError.__str__ and to_dict must not leak credentials."""

    def test_str_does_not_expose_password(self):
        err = BaseError("conn failed", details={"url": "postgresql://u:topsecret@host/db"})
        assert "topsecret" not in str(err)

    def test_str_does_not_expose_token(self):
        err = BaseError("auth failed", details={"token": "my_api_token_xyz"})
        assert "my_api_token_xyz" not in str(err)

    def test_to_dict_does_not_expose_password(self):
        err = BaseError("oops", details={"dsn": "redis://:secret@cache:6379"})
        d = err.to_dict()
        assert "secret" not in str(d)

    def test_to_dict_does_not_expose_api_key(self):
        err = BaseError("oops", details={"api_key": "sk-hunter2"})
        d = err.to_dict()
        assert "sk-hunter2" not in str(d)

    def test_raw_details_still_accessible(self):
        """The raw details dict must remain unmodified (redaction is display-time only)."""
        err = BaseError("oops", details={"url": "postgresql://u:pw@host/db"})
        assert err.details["url"] == "postgresql://u:pw@host/db"

    def test_non_sensitive_details_preserved_in_str(self):
        err = BaseError("err", details={"adapter": "postgres", "table": "users"})
        s = str(err)
        assert "adapter='postgres'" in s
        assert "table='users'" in s

    def test_long_detail_truncated_in_str(self):
        err = BaseError("err", details={"data": "A" * 600})
        s = str(err)
        assert "truncated" in s

    def test_postgresql_asyncpg_url_redacted(self):
        url = "postgresql+asyncpg://alice:hunter2@db.example.com:5432/prod"
        err = BaseError("fail", details={"url": url})
        assert "hunter2" not in str(err)
        assert "hunter2" not in str(err.to_dict())

    def test_mongodb_srv_url_redacted(self):
        url = "mongodb+srv://root:Pa$$w0rd@cluster.example.net/app"
        err = BaseError("fail", details={"url": url})
        assert "Pa$$w0rd" not in str(err)


# ---------------------------------------------------------------------------
# ConnectionError (M11-adjacent) tests
# ---------------------------------------------------------------------------


class TestConnectionErrorRedaction:
    """Connection errors often carry DSNs — verify redaction at the exception layer."""

    def test_connection_error_url_not_leaked(self):
        err = AdapterConnectionError(
            "Could not connect",
            url="postgresql://admin:supersecret@prod-db:5432/app",
        )
        assert "supersecret" not in str(err)
        assert "supersecret" not in str(err.to_dict())


# ---------------------------------------------------------------------------
# ConfigurationError (M11) tests
# ---------------------------------------------------------------------------


class TestConfigurationErrorM11:
    """ConfigurationError must not expose the raw config dict."""

    def test_config_password_not_leaked(self):
        config = {
            "host": "db.example.com",
            "port": 5432,
            "user": "admin",
            "password": "db_password_123",
        }
        err = ConfigurationError("Bad config", config=config)
        assert "db_password_123" not in str(err)
        assert "db_password_123" not in str(err.to_dict())

    def test_config_dsn_not_leaked(self):
        config = {"dsn": "postgresql://user:pw123@host/db", "pool_size": 5}
        err = ConfigurationError("Bad config", config=config)
        assert "pw123" not in str(err)
        assert "pw123" not in str(err.to_dict())

    def test_config_api_key_not_leaked(self):
        config = {"api_key": "wvt-key-abc123", "endpoint": "https://api.example.com"}
        err = ConfigurationError("Bad config", config=config)
        assert "wvt-key-abc123" not in str(err)

    def test_non_sensitive_config_keys_visible(self):
        """Non-sensitive config fields should remain visible for debugging."""
        config = {"host": "localhost", "port": 5432}
        err = ConfigurationError("Bad config", config=config)
        # host and port are not sensitive keys — they should appear
        d = err.to_dict()
        details_str = str(d)
        assert "localhost" in details_str
        assert "5432" in details_str
