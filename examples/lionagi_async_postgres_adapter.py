"""
Improved LionAGI async PostgreSQL adapter leveraging pydapter v1.0.2+ CRUD operations.

This adapter is optimized for lionagi Nodes with auto-table creation and proper
field mapping for the lionagi schema.
"""

from __future__ import annotations

from typing import ClassVar, TypeVar

import sqlalchemy as sa
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from sqlalchemy.ext.asyncio import create_async_engine

T = TypeVar("T")


class LionAGIAsyncPostgresAdapter(AsyncPostgresAdapter[T]):
    """
    Zero-config async PostgreSQL adapter for lionagi Nodes.
    
    Features:
    - Auto-creates tables with lionagi schema
    - Handles both PostgreSQL and SQLite connections
    - Optimized for lionagi Element/Node operations
    - Support for ORDER BY via raw SQL
    """

    obj_key: ClassVar[str] = "lionagi_async_pg"

    @classmethod
    async def from_obj(
        cls,
        subj_cls,
        obj,
        /,
        *,
        many: bool = True,
        adapt_meth: str = None,
        **kw,
    ):
        """
        Read lionagi Nodes from database with enhanced features.
        
        For ORDER BY operations, use raw_sql:
        ```python
        config = {
            "dsn": "sqlite:///app.db",
            "operation": "raw_sql",
            "sql": "SELECT * FROM nodes ORDER BY created_at DESC LIMIT :limit",
            "params": {"limit": 10}
        }
        recent_nodes = await adapter.from_obj(Node, config, many=True)
        ```
        """
        # Default adapt_meth for lionagi Elements
        if adapt_meth is None and hasattr(subj_cls, 'from_dict'):
            adapt_meth = 'from_dict'
        
        # For raw SQL operations, we don't need any special handling anymore
        # pydapter now properly handles raw SQL without table inspection
        return await super().from_obj(
            subj_cls, obj, many=many, adapt_meth=adapt_meth, **kw
        )

    @classmethod
    async def to_obj(
        cls,
        subj,
        /,
        *,
        many: bool = True,
        adapt_meth: str = None,
        **kw,
    ):
        """
        Write lionagi Node(s) to database with auto-table creation.
        
        Automatically creates the table with lionagi schema if it doesn't exist:
        - id (String, primary key)
        - content (JSON/JSONB)
        - node_metadata (JSON/JSONB) 
        - created_at (DateTime)
        - embedding (JSON/JSONB, nullable)
        """
        # Default adapt_meth for lionagi Elements
        if adapt_meth is None and hasattr(subj, 'to_dict'):
            adapt_meth = 'to_dict'
            # Set mode for proper serialization
            kw.setdefault('mode', 'db')
        
        # Auto-create table if needed
        if table := kw.get("table"):
            if engine_url := (kw.get("dsn") or kw.get("engine_url")):
                await cls._ensure_table(engine_url, table)
            elif engine := kw.get("engine"):
                await cls._ensure_table(engine, table)

        return await super().to_obj(
            subj, many=many, adapt_meth=adapt_meth, **kw
        )

    @classmethod
    async def _ensure_table(cls, engine_or_url, table_name: str):
        """Create table with lionagi schema if it doesn't exist."""
        # Handle both engine and URL
        should_dispose = False
        if isinstance(engine_or_url, str):
            # Determine the appropriate engine based on DSN
            if engine_or_url.startswith('sqlite'):
                # For SQLite, use basic JSON type
                engine = create_async_engine(engine_or_url, future=True)
                json_type = sa.JSON
            else:
                # For PostgreSQL, use JSONB for better performance
                engine = create_async_engine(engine_or_url, future=True)
                json_type = sa.dialects.postgresql.JSONB
            should_dispose = True
        else:
            engine = engine_or_url
            # Determine JSON type based on engine URL
            engine_url = str(engine.url)
            json_type = (
                sa.dialects.postgresql.JSONB
                if "postgresql" in engine_url
                else sa.JSON
            )
            should_dispose = False

        try:
            async with engine.begin() as conn:
                # Create table with lionagi schema
                await conn.run_sync(
                    lambda sync_conn: sa.Table(
                        table_name,
                        sa.MetaData(),
                        sa.Column("id", sa.String, primary_key=True),
                        sa.Column("content", json_type),
                        sa.Column("node_metadata", json_type),
                        sa.Column("created_at", sa.DateTime),
                        sa.Column("embedding", json_type, nullable=True),
                    ).create(sync_conn, checkfirst=True)
                )
        finally:
            if should_dispose:
                await engine.dispose()

    @classmethod
    async def get_recent(
        cls,
        subj_cls,
        *,
        dsn: str,
        table: str,
        limit: int = 10,
        order_by: str = "created_at DESC",
        **kw
    ):
        """
        Convenience method to get recent records with ORDER BY.
        
        This method uses raw SQL to properly support ORDER BY operations.
        
        Args:
            subj_cls: The model class (e.g., Node)
            dsn: Database connection string
            table: Table name
            limit: Number of records to return
            order_by: ORDER BY clause (default: "created_at DESC")
            **kw: Additional adapter arguments
        
        Returns:
            List of model instances ordered as specified
        
        Example:
            ```python
            recent_nodes = await LionAGIAsyncPostgresAdapter.get_recent(
                Node,
                dsn="sqlite:///app.db",
                table="nodes",
                limit=20,
                order_by="created_at DESC"
            )
            ```
        """
        config = {
            "dsn": dsn,
            "operation": "raw_sql",
            "sql": f"SELECT * FROM {table} ORDER BY {order_by} LIMIT :limit",
            "params": {"limit": limit}
        }
        
        # Use from_dict for lionagi Elements
        adapt_meth = kw.get('adapt_meth', 'from_dict' if hasattr(subj_cls, 'from_dict') else 'model_validate')
        
        return await cls.from_obj(
            subj_cls, 
            config, 
            many=True,
            adapt_meth=adapt_meth,
            **kw
        )

    @classmethod
    async def search_by_content(
        cls,
        subj_cls,
        *,
        dsn: str,
        table: str,
        search_term: str,
        limit: int = 10,
        **kw
    ):
        """
        Search nodes by content field using SQL JSON operators.
        
        Args:
            subj_cls: The model class
            dsn: Database connection string
            table: Table name
            search_term: Text to search for in content
            limit: Maximum results
        
        Returns:
            List of matching nodes
        
        Example:
            ```python
            results = await adapter.search_by_content(
                Node,
                dsn="postgresql://localhost/db",
                table="nodes",
                search_term="important",
                limit=5
            )
            ```
        """
        # Determine SQL based on database type
        if "sqlite" in dsn:
            # SQLite JSON query
            sql = f"""
                SELECT * FROM {table}
                WHERE json_extract(content, '$') LIKE :search
                ORDER BY created_at DESC
                LIMIT :limit
            """
        else:
            # PostgreSQL JSONB query
            sql = f"""
                SELECT * FROM {table}
                WHERE content::text ILIKE :search
                ORDER BY created_at DESC
                LIMIT :limit
            """
        
        config = {
            "dsn": dsn,
            "operation": "raw_sql",
            "sql": sql,
            "params": {
                "search": f"%{search_term}%",
                "limit": limit
            }
        }
        
        adapt_meth = kw.get('adapt_meth', 'from_dict' if hasattr(subj_cls, 'from_dict') else 'model_validate')
        
        return await cls.from_obj(
            subj_cls,
            config,
            many=True,
            adapt_meth=adapt_meth,
            **kw
        )

    @classmethod
    async def bulk_upsert(
        cls,
        nodes,
        *,
        dsn: str,
        table: str,
        conflict_columns: list[str] = None,
        **kw
    ):
        """
        Efficiently upsert multiple nodes.
        
        Args:
            nodes: List of Node instances
            dsn: Database connection string
            table: Table name
            conflict_columns: Columns that define uniqueness (default: ["id"])
        
        Returns:
            Dict with inserted_count, updated_count, and total_count
        
        Example:
            ```python
            result = await adapter.bulk_upsert(
                nodes,
                dsn="postgresql://localhost/db",
                table="nodes",
                conflict_columns=["id"]
            )
            print(f"Inserted: {result['inserted_count']}, Updated: {result['updated_count']}")
            ```
        """
        if conflict_columns is None:
            conflict_columns = ["id"]
        
        # Ensure table exists
        await cls._ensure_table(dsn, table)
        
        # Use to_dict with db mode for lionagi Elements
        adapt_meth = 'to_dict' if hasattr(nodes[0], 'to_dict') else 'model_dump'
        
        return await cls.to_obj(
            nodes,
            dsn=dsn,
            table=table,
            operation="upsert",
            conflict_columns=conflict_columns,
            adapt_meth=adapt_meth,
            mode='db' if adapt_meth == 'to_dict' else None,
            many=True,
            **kw
        )


# Usage example for lionagi
if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    
    # Mock Node class for demonstration
    class Node:
        def __init__(self, id, content, created_at=None):
            self.id = id
            self.content = content
            self.created_at = created_at or datetime.now()
        
        def to_dict(self, mode="python"):
            if mode == "db":
                return {
                    "id": str(self.id),
                    "content": self.content,
                    "node_metadata": {"lion_class": "Node"},
                    "created_at": self.created_at.isoformat(),
                    "embedding": None
                }
            return {
                "id": self.id,
                "content": self.content,
                "metadata": {"lion_class": "Node"},
                "created_at": self.created_at.timestamp()
            }
        
        @classmethod
        def from_dict(cls, data):
            # Handle both db and python formats
            if "node_metadata" in data:
                # From database
                return cls(
                    id=data["id"],
                    content=data["content"],
                    created_at=datetime.fromisoformat(data["created_at"])
                )
            else:
                # From python
                return cls(
                    id=data["id"],
                    content=data["content"],
                    created_at=datetime.fromtimestamp(data.get("created_at", 0))
                )
    
    async def demo():
        adapter = LionAGIAsyncPostgresAdapter
        dsn = "sqlite:///test_lionagi.db"
        
        # Create some nodes
        nodes = [
            Node(f"node_{i}", {"text": f"Content {i}"})
            for i in range(5)
        ]
        
        # Bulk upsert
        result = await adapter.bulk_upsert(
            nodes,
            dsn=dsn,
            table="nodes"
        )
        print(f"Upserted: {result}")
        
        # Get recent nodes with ORDER BY
        recent = await adapter.get_recent(
            Node,
            dsn=dsn,
            table="nodes",
            limit=3
        )
        print(f"Recent nodes: {[n.id for n in recent]}")
        
        # Search by content
        results = await adapter.search_by_content(
            Node,
            dsn=dsn,
            table="nodes",
            search_term="Content",
            limit=2
        )
        print(f"Search results: {[n.id for n in results]}")
    
    # asyncio.run(demo())