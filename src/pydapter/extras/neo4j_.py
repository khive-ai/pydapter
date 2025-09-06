"""
Neo4j adapter (requires `neo4j`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import neo4j
import neo4j.exceptions
from neo4j import GraphDatabase

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class Neo4jAdapter(Adapter[T]):
    """
    Neo4j graph database adapter for converting between Pydantic models and Neo4j nodes/relationships.

    This adapter provides methods to:
    - Execute Cypher queries and convert results to Pydantic models
    - Create nodes and relationships from Pydantic models
    - Handle Neo4j connection management and error handling
    - Support for complex graph operations and traversals

    Attributes:
        obj_key: The key identifier for this adapter type ("neo4j")

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.extras.neo4j_ import Neo4jAdapter
        from neo4j import basic_auth

        class Person(BaseModel):
            name: str
            age: int
            city: str

        # Query from Neo4j
        query_config = {
            "url": "bolt://localhost:7687",
            "auth": basic_auth("neo4j", "password"),
            "query": "MATCH (p:Person) WHERE p.age >= 18 RETURN p.name, p.age, p.city"
        }
        people = Neo4jAdapter.from_obj(Person, query_config, many=True)

        # Create nodes in Neo4j
        create_config = {
            "url": "bolt://localhost:7687",
            "auth": basic_auth("neo4j", "password"),
            "query": "CREATE (p:Person {name: $name, age: $age, city: $city})"
        }
        new_people = [Person(name="John", age=30, city="NYC")]
        Neo4jAdapter.to_obj(new_people, create_config, many=True)
        ```
    """

    obj_key = "neo4j"

    @classmethod
    def _create_driver(cls, url: str, auth=None) -> neo4j.Driver:
        """
        Create a Neo4j driver with proper error handling.

        Args:
            url: Neo4j connection URL (e.g., "bolt://localhost:7687")
            auth: Authentication tuple or None for no auth

        Returns:
            neo4j.Driver instance

        Raises:
            ConnectionError: If connection cannot be established or auth fails
        """
        try:
            if auth:
                return GraphDatabase.driver(url, auth=auth)
            else:
                return GraphDatabase.driver(url)
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
        """Basic validation for Cypher queries to prevent injection."""
        # Check for unescaped backticks in label names
        if re.search(r"`[^`]*`[^`]*`", cypher):
            raise QueryError.from_adapter(
                cls,
                "Invalid Cypher query: Possible injection in label name",
                query=cypher,
            )

    # incoming
    @classmethod
    def from_obj(
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
        # Validate required parameters
        if "url" not in obj:
            raise ValidationError.from_adapter(
                cls, "Missing required parameter 'url'", data=obj
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
                cls, "Error executing Neo4j query", query=cypher, cause=e
            )
        finally:
            driver.close()

        # Handle empty result set
        if not rows:
            if many:
                return []
            raise ResourceError.from_adapter(
                cls,
                "No nodes found matching the query",
                resource=label,
                where_clause=obj.get("where", ""),
            )

        # Convert rows to model instances
        try:
            if many:
                return [adapt_from(subj_cls, r, adapt_meth, adapt_kw) for r in rows]
            return adapt_from(subj_cls, rows[0], adapt_meth, adapt_kw)
        except Exception as e:
            raise ValidationError.from_adapter(
                cls,
                "Data conversion failed",
                data=rows[0] if not many else rows,
                adapt_method=adapt_meth,
                cause=e,
            )

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
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ):
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
        driver = cls._create_driver(url, auth=auth)

        try:
            with driver.session() as s:
                results = []
                for it in items:
                    props = adapt_dump(it, adapt_meth, adapt_kw)

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
                    try:
                        result = s.run(cypher, val=props[merge_on], props=props)
                        results.append(result)
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
                            cls, "Error executing Neo4j query", query=cypher, cause=e
                        )

                return {"merged_count": len(results)}
        finally:
            driver.close()
