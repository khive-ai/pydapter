"""
Neo4j adapter (requires `neo4j`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypeVar

import neo4j
import neo4j.exceptions
from neo4j import GraphDatabase
from pydantic import BaseModel, ValidationError

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class Neo4jAdapter(Adapter[T]):
    obj_key = "neo4j"

    @classmethod
    def _create_driver(cls, url: str, auth=None) -> neo4j.Driver:
        """Create a Neo4j driver with error handling."""
        try:
            if auth:
                return GraphDatabase.driver(url, auth=auth)
            else:
                return GraphDatabase.driver(url)
        except neo4j.exceptions.ServiceUnavailable as e:
            raise ConnectionError(
                f"Neo4j service unavailable: {e}", adapter="neo4j", url=url
            ) from e
        except neo4j.exceptions.AuthError as e:
            raise ConnectionError(
                f"Neo4j authentication failed: {e}", adapter="neo4j", url=url
            ) from e
        except Exception as e:
            raise ConnectionError(
                f"Failed to create Neo4j driver: {e}", adapter="neo4j", url=url
            ) from e

    @classmethod
    def _validate_cypher(cls, cypher: str) -> None:
        """Basic validation for Cypher queries to prevent injection."""
        # Check for unescaped backticks in label names
        if re.search(r"`[^`]*`[^`]*`", cypher):
            raise QueryError(
                "Invalid Cypher query: Possible injection in label name",
                query=cypher,
                adapter="neo4j",
            )

    # incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        try:
            # Validate required parameters
            if "url" not in obj:
                raise AdapterValidationError(
                    "Missing required parameter 'url'", data=obj
                )

            # Create driver
            auth = obj.get("auth")
            driver = cls._create_driver(obj["url"], auth=auth)

            # Prepare Cypher query
            label = obj.get("label", subj_cls.__name__)
            where = f"WHERE {obj['where']}" if "where" in obj else ""
            cypher = f"MATCH (n:`{label}`) {where} RETURN n"

            # Validate Cypher query
            cls._validate_cypher(cypher)

            # Execute query
            try:
                with driver.session() as s:
                    result = s.run(cypher)
                    rows = [r["n"]._properties for r in result]
            except neo4j.exceptions.CypherSyntaxError as e:
                raise QueryError(
                    f"Neo4j Cypher syntax error: {e}",
                    query=cypher,
                    adapter="neo4j",
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
                    adapter="neo4j",
                ) from e
            except Exception as e:
                raise QueryError(
                    f"Error executing Neo4j query: {e}",
                    query=cypher,
                    adapter="neo4j",
                ) from e
            finally:
                driver.close()

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

        except (ConnectionError, QueryError, ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(f"Unexpected error in Neo4j adapter: {e}", adapter="neo4j")

    # outgoing
    @classmethod
    def to_obj(
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
            driver = cls._create_driver(url, auth=auth)

            try:
                with driver.session() as s:
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
                            result = s.run(cypher, val=props[merge_on], props=props)
                            results.append(result)
                        except neo4j.exceptions.CypherSyntaxError as e:
                            raise QueryError(
                                f"Neo4j Cypher syntax error: {e}",
                                query=cypher,
                                adapter="neo4j",
                            ) from e
                        except neo4j.exceptions.ConstraintError as e:
                            raise QueryError(
                                f"Neo4j constraint violation: {e}",
                                query=cypher,
                                adapter="neo4j",
                            ) from e
                        except Exception as e:
                            raise QueryError(
                                f"Error executing Neo4j query: {e}",
                                query=cypher,
                                adapter="neo4j",
                            ) from e

                    return {"merged_count": len(results)}
            finally:
                driver.close()

        except (ConnectionError, QueryError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise QueryError(f"Unexpected error in Neo4j adapter: {e}", adapter="neo4j")
