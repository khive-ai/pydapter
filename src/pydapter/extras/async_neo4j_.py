"""AsyncNeo4jAdapter, obj_key = 'async_neo4j'"""

from __future__ import annotations

import re
from collections.abc import Sequence

import neo4j
import neo4j.exceptions
from neo4j import AsyncGraphDatabase

from ..async_core import AsyncAdapter
from ..exceptions import (
    ConnectionError,
    ParseError,
    QueryError,
    ResourceError,
    ValidationError,
)
from ..utils import T, adapt_dump, adapt_from


class AsyncNeo4jAdapter(AsyncAdapter[T]):
    """
    Asynchronous adapter for Neo4j graph database.

    This adapter provides methods to convert between Pydantic models and Neo4j nodes,
    with full support for asynchronous operations.
    """

    obj_key = "async_neo4j"

    # Class variable for driver factory - makes testing easier
    _driver_factory = AsyncGraphDatabase.driver

    def __init__(self, url=None, auth=None, **kwargs):
        """Initialize the adapter with connection parameters.

        Args:
            url: Neo4j connection URL
            auth: Optional authentication tuple (username, password)
            **kwargs: Additional keyword arguments
        """
        self.url = url
        self.auth = auth
        self.kwargs = kwargs
        self._driver = None
        self._session = None

    @classmethod
    def set_driver_factory(cls, factory):
        """Set the driver factory for testing purposes."""
        cls._driver_factory = factory

    @classmethod
    def reset_driver_factory(cls):
        """Reset the driver factory to the default."""
        cls._driver_factory = AsyncGraphDatabase.driver

    @classmethod
    async def _create_driver(cls, url: str, auth=None) -> neo4j.AsyncDriver:
        """Create a Neo4j async driver with error handling.

        Args:
            url: Neo4j connection URL
            auth: Optional authentication tuple (username, password)

        Returns:
            neo4j.AsyncDriver: Configured Neo4j async driver

        Raises:
            ConnectionError: If connection to Neo4j fails
        """
        try:
            if auth:
                return cls._driver_factory(url, auth=auth)
            else:
                return cls._driver_factory(url)
        except neo4j.exceptions.ServiceUnavailable as e:
            raise ConnectionError.from_adapter(
                cls, "Neo4j service unavailable", url=url, cause=e
            )
        except neo4j.exceptions.AuthError as e:
            raise ConnectionError.from_adapter(
                cls, "Neo4j authentication failed", url=url, cause=e
            )
        except Exception as e:
            raise ConnectionError.from_adapter(
                cls, "Failed to create Neo4j driver", url=url, cause=e
            )

    @classmethod
    def _validate_cypher(cls, cypher: str) -> None:
        """Basic validation for Cypher queries to prevent injection.

        Args:
            cypher: Cypher query string to validate

        Raises:
            QueryError: If the query contains potentially unsafe patterns
        """
        # Check for unescaped backticks in label names
        if re.search(r"`[^`]*`[^`]*`", cypher):
            raise QueryError.from_adapter(
                cls,
                "Invalid Cypher query: Possible injection in label name",
                query=cypher,
            )

    # incoming
    @classmethod
    async def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        """
        Convert from Neo4j nodes to Pydantic models asynchronously.

        Args:
            subj_cls: Target model class
            obj: Dictionary with query parameters
            many: Whether to return multiple results
            **kw: Additional keyword arguments

        Required parameters in obj:
            url: Neo4j connection URL

        Optional parameters in obj:
            auth: Authentication tuple (username, password)
            label: Node label (defaults to model class name)
            where: Cypher WHERE clause

        Returns:
            T | list[T]: Single model instance or list of model instances

        Raises:
            ValidationError: If required parameters are missing
            ConnectionError: If connection to Neo4j fails
            QueryError: If query execution fails
            ResourceError: If no matching nodes are found

        search:exa-v1w2x3y4 - Async pattern for Neo4j query execution
        search:pplx-z5a6b7c8 - Error handling in async Neo4j operations
        """
        # Validate required parameters
        if "url" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'url'", data=obj
            )

        # Create driver
        auth = obj.get("auth")
        driver = await cls._create_driver(obj["url"], auth=auth)

        # Prepare Cypher query
        label = obj.get("label", subj_cls.__name__)
        where = f"WHERE {obj['where']}" if "where" in obj else ""
        cypher = f"MATCH (n:`{label}`) {where} RETURN n"

        # Validate Cypher query
        cls._validate_cypher(cypher)

        # Execute query
        session = driver.session()
        try:
            result = await session.run(cypher)
            rows = []
            async for r in result:
                try:
                    # Extract Neo4j node properties - this can fail with Neo4j data type parsing errors
                    # (DateTime conversion, Point/spatial types, Duration, etc.)
                    rows.append(r["n"]._properties)
                except (TypeError, ValueError, AttributeError) as e:
                    # Handle Neo4j data type parsing/conversion errors
                    raise ParseError.from_adapter(
                        cls,
                        "Error parsing Neo4j data types to Python objects",
                        data=str(r["n"]),
                        cause=e,
                    )

            # Handle empty result set
            if not rows:
                if many:
                    return []
                raise ResourceError.from_adapter(
                    cls,
                    "No nodes found matching the query",
                    resource=label,
                    where=obj.get("where", ""),
                )

            # Convert rows to model instances
            if many:
                return [adapt_from(subj_cls, r, adapt_meth, adapt_kw) for r in rows]
            return adapt_from(subj_cls, rows[0], adapt_meth, adapt_kw)

        except (
            ResourceError,
            QueryError,
            ValidationError,
            ConnectionError,
            ParseError,
        ):
            # Let our custom errors bubble up directly
            raise
        except neo4j.exceptions.CypherSyntaxError as e:
            raise QueryError.from_adapter(
                cls, "Neo4j Cypher syntax error", query=cypher, cause=e
            )
        except neo4j.exceptions.ClientError as e:
            if "not found" in str(e).lower():
                raise ResourceError.from_adapter(
                    cls, "Neo4j resource not found", resource=label, cause=e
                )
            raise QueryError.from_adapter(
                cls, "Neo4j client error", query=cypher, cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Unexpected error in async Neo4j adapter", cause=e
            )
        finally:
            if session:
                try:
                    await session.close()
                except Exception:
                    pass

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        url,
        auth=None,
        label=None,
        merge_on="id",
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
        """
        Convert from Pydantic models to Neo4j nodes asynchronously.

        Args:
            subj: Model instance or sequence of model instances
            url: Neo4j connection URL
            auth: Optional authentication tuple (username, password)
            label: Node label (defaults to model class name)
            merge_on: Property to use for MERGE operation (defaults to "id")
            **kw: Additional keyword arguments

        Returns:
            dict: Operation result with count of merged nodes

        Raises:
            ValidationError: If required parameters are missing
            ConnectionError: If connection to Neo4j fails
            QueryError: If query execution fails

        search:pplx-d9e0f1g2 - Neo4j MERGE operation best practices
        search:exa-h3i4j5k6 - Async batch operations with Neo4j
        """
        # Validate required parameters
        if not url:
            raise ValidationError.from_adapter(cls, "Missing required parameter 'url'")
        if not merge_on:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'merge_on'"
            )

        # Prepare data
        items = subj if isinstance(subj, Sequence) else [subj]
        if not items:
            return None  # Nothing to insert

        # Get label from first item if not provided
        label = label or items[0].__class__.__name__

        # Create driver
        driver = await cls._create_driver(url, auth=auth)

        session = driver.session()
        try:
            results = []
            for it in items:
                try:
                    props = adapt_dump(it, adapt_meth, adapt_kw)
                except (TypeError, ValueError, AttributeError) as e:
                    # Handle data parsing/conversion errors when serializing Pydantic to Neo4j
                    raise ParseError.from_adapter(
                        cls,
                        "Error converting Pydantic model to Neo4j properties",
                        data=adapt_dump(it, "model_dump", None),
                        cause=e,
                    )

                # Check if merge_on property exists
                if merge_on not in props:
                    raise ValidationError.from_adapter(
                        cls,
                        f"Merge property '{merge_on}' not found in model",
                        data=props,
                    )

                # Prepare and validate Cypher query
                cypher = f"MERGE (n:`{label}` {{{merge_on}: $val}}) SET n += $props"
                cls._validate_cypher(cypher)

                # Execute query
                result = await session.run(cypher, val=props[merge_on], props=props)
                results.append(result)

            return {"merged_count": len(results)}

        except (
            ResourceError,
            QueryError,
            ValidationError,
            ConnectionError,
            ParseError,
        ):
            # Let our custom errors bubble up directly
            raise
        except neo4j.exceptions.CypherSyntaxError as e:
            raise QueryError.from_adapter(
                cls, "Neo4j Cypher syntax error", query=cypher, cause=e
            )
        except neo4j.exceptions.ConstraintError as e:
            raise QueryError.from_adapter(
                cls, "Neo4j constraint violation", query=cypher, cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Unexpected error in async Neo4j adapter", cause=e
            )
        finally:
            if session:
                try:
                    await session.close()
                except Exception:
                    pass

    async def __aenter__(self):
        """Async context manager entry.

        Returns:
            self: The adapter instance

        Raises:
            ConnectionError: If connection to Neo4j fails
        """
        if not self.url:
            raise ConnectionError.from_adapter(
                self.__class__, "URL is required for Neo4j connection"
            )

        self._driver = await self._create_driver(self.url, auth=self.auth)
        try:
            # For the mock tests, we don't need to await the session
            self._session = self._driver.session()
            return self
        except Exception as e:
            # Clean up driver if session creation fails
            if self._driver:
                await self._driver.close()
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if self._session:
            try:
                await self._session.close()
            except Exception:
                # Ignore errors during session close
                pass

        if self._driver:
            try:
                await self._driver.close()
            except Exception:
                # Ignore errors during driver close
                pass

    async def query(self, cypher, **params):
        """Execute a Cypher query and return the results.

        Args:
            cypher: Cypher query string
            **params: Query parameters

        Returns:
            list: List of query results

        Raises:
            QueryError: If the query execution fails
        """
        if not self._session:
            raise QueryError.from_adapter(
                self.__class__,
                "No active session. Use AsyncNeo4jAdapter as a context manager.",
            )

        # Validate Cypher query
        self._validate_cypher(cypher)

        try:
            # Execute the query - don't await the run method itself
            result = self._session.run(cypher, **params)

            # Process the results
            rows = []
            async for r in result:
                rows.append(r["n"]._properties)

            return rows
        except neo4j.exceptions.CypherSyntaxError as e:
            raise QueryError.from_adapter(
                self.__class__, "Neo4j Cypher syntax error", query=cypher, cause=e
            )
        except Exception as e:
            raise QueryError.from_adapter(
                self.__class__, "Error executing Neo4j query", query=cypher, cause=e
            )
