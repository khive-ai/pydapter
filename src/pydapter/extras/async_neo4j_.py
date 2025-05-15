"""
AsyncNeo4jAdapter - Asynchronous adapter for Neo4j graph database.

This adapter provides asynchronous access to Neo4j using the AsyncGraphDatabase.
It follows the AsyncAdapter protocol and provides comprehensive error handling and
resource management.

search:pplx-a7b2c - Neo4j Python Driver async API best practices
search:exa-f9d3e - Asynchronous Neo4j operations with proper error handling
search:pplx-d8f4g - Proper error handling in async Neo4j operations
search:exa-h6j9k - Testing async Neo4j adapters with mocks
search:pplx-l2m5n - Efficient connection management in Neo4j async drivers
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import neo4j
import neo4j.exceptions
from neo4j import AsyncGraphDatabase
from pydantic import ValidationError

from ..async_core import AsyncAdapter, T
from ..exceptions import ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

# T is already imported from async_core


class AsyncNeo4jAdapter(AsyncAdapter[T]):
    """
    Asynchronous adapter for Neo4j graph database.

    This adapter provides methods to convert between Pydantic models and Neo4j nodes,
    with full support for asynchronous operations.
    """

    obj_key = "async_neo4j"

    # Class variable for driver factory - makes testing easier
    _driver_factory = AsyncGraphDatabase.driver

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
            raise ConnectionError(
                f"Neo4j service unavailable: {e}", adapter="async_neo4j", url=url
            ) from e
        except neo4j.exceptions.AuthError as e:
            raise ConnectionError(
                f"Neo4j authentication failed: {e}", adapter="async_neo4j", url=url
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to create Neo4j driver: {e}", adapter="async_neo4j", url=url
            ) from e

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
            raise QueryError(
                "Invalid Cypher query: Possible injection in label name",
                query=cypher,
                adapter="async_neo4j",
            )

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
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
            AdapterValidationError: If required parameters are missing
            ConnectionError: If connection to Neo4j fails
            QueryError: If query execution fails
            ResourceError: If no matching nodes are found

        search:exa-v1w2x3y4 - Async pattern for Neo4j query execution
        search:pplx-z5a6b7c8 - Error handling in async Neo4j operations
        """
        try:
            # Validate required parameters
            if "url" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'url'", data=obj
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
            try:
                # Use the driver directly without nested context managers
                session = driver.session()
                try:
                    try:
                        # Execute the query
                        result = await session.run(cypher)
                        # Process the results
                        rows = []
                        async for r in result:
                            rows.append(r["n"]._properties)
                    except neo4j.exceptions.CypherSyntaxError as e:
                        raise QueryError(
                            f"Neo4j Cypher syntax error: {e}",
                            query=cypher,
                            adapter="async_neo4j",
                        ) from e
                    except neo4j.exceptions.ClientError as e:
                        if "not found" in str(e).lower():
                            raise ResourceError(
                                f"Neo4j resource not found: {e}",
                                resource=label,
                            ) from e
                        raise QueryError(
                            f"Neo4j client error: {e}",
                            query=cypher,
                            adapter="async_neo4j",
                        ) from e
                    except Exception as e:
                        raise QueryError(
                            f"Error executing Neo4j query: {e}",
                            query=cypher,
                            adapter="async_neo4j",
                        ) from e

                    # Handle empty result set
                    if not rows:
                        if many:
                            return []
                        raise ResourceError(
                            "No nodes found matching the query",
                            resource=label,
                            where=obj.get("where", ""),
                        )

                    # Convert rows to model instances
                    try:
                        if many:
                            return [subj_cls.model_validate(r) for r in rows]
                        return subj_cls.model_validate(rows[0])
                    except ValidationError as e:
                        raise AdapterValidationError(
                            f"Validation error: {e}",
                            data=rows[0] if not many else rows,
                            errors=e.errors(),
                        ) from e
                finally:
                    if session:
                        try:
                            await session.close()
                        except Exception:
                            # Ignore errors during session close
                            pass

            except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Wrap other exceptions
                raise QueryError(
                    f"Error in Neo4j query: {e}",
                    adapter="async_neo4j",
                ) from e

        except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(
                f"Unexpected error in async Neo4j adapter: {e}", adapter="async_neo4j"
            ) from e

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
            AdapterValidationError: If required parameters are missing
            ConnectionError: If connection to Neo4j fails
            QueryError: If query execution fails

        search:pplx-d9e0f1g2 - Neo4j MERGE operation best practices
        search:exa-h3i4j5k6 - Async batch operations with Neo4j
        """
        try:
            # Validate required parameters
            if not url:
                raise AdapterValidationError("Missing required parameter 'url'")
            if not merge_on:
                raise AdapterValidationError("Missing required parameter 'merge_on'")

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return None  # Nothing to insert

            # Get label from first item if not provided
            label = label or items[0].__class__.__name__

            # Create driver
            driver = await cls._create_driver(url, auth=auth)

            try:
                # Use the driver directly without nested context managers
                session = driver.session()
                try:
                    results = []
                    for it in items:
                        props = it.model_dump()

                        # Check if merge_on property exists
                        if merge_on not in props:
                            raise AdapterValidationError(
                                f"Merge property '{merge_on}' not found in model",
                                data=props,
                            )

                        # Prepare and validate Cypher query
                        cypher = (
                            f"MERGE (n:`{label}` {{{merge_on}: $val}}) SET n += $props"
                        )
                        cls._validate_cypher(cypher)

                        # Execute query
                        try:
                            # Execute the query
                            result = await session.run(
                                cypher, val=props[merge_on], props=props
                            )
                            # Add to results
                            results.append(result)
                        except neo4j.exceptions.CypherSyntaxError as e:
                            raise QueryError(
                                f"Neo4j Cypher syntax error: {e}",
                                query=cypher,
                                adapter="async_neo4j",
                            ) from e
                        except neo4j.exceptions.ConstraintError as e:
                            raise QueryError(
                                f"Neo4j constraint violation: {e}",
                                query=cypher,
                                adapter="async_neo4j",
                            ) from e
                        except Exception as e:
                            raise QueryError(
                                f"Error executing Neo4j query: {e}",
                                query=cypher,
                                adapter="async_neo4j",
                            ) from e

                    return {"merged_count": len(results)}
                finally:
                    if session:
                        try:
                            await session.close()
                        except Exception:
                            # Ignore errors during session close
                            pass

            except (ConnectionError, QueryError, AdapterValidationError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Wrap other exceptions
                raise QueryError(
                    f"Error in Neo4j operation: {e}",
                    adapter="async_neo4j",
                ) from e

        except (ConnectionError, QueryError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(
                f"Unexpected error in async Neo4j adapter: {e}", adapter="async_neo4j"
            ) from e
