"""
Memvid adapter - uses `memvid` for video-based AI memory.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class MemvidAdapter(Adapter[T]):
    """
    Memvid adapter for converting between Pydantic models and video-based memory storage.

    This adapter provides methods to:
    - Build video memories from Pydantic models and search them semantically
    - Retrieve similar content from video memories and convert to Pydantic models
    - Handle text chunking, embedding, and video encoding operations
    - Support for PDF processing and various text formats

    Attributes:
        obj_key: The key identifier for this adapter type ("memvid")

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.extras.memvid_ import MemvidAdapter

        class Document(BaseModel):
            id: str
            text: str
            category: str

        # Build video memory from documents
        docs = [Document(id="1", text="Sample content", category="tech")]
        build_config = {
            "video_file": "memory.mp4",
            "index_file": "memory_index.json",
            "text_field": "text",
            "chunk_size": 512,
            "overlap": 50
        }
        MemvidAdapter.to_obj(docs, build_config, many=True)

        # Search video memory
        search_config = {
            "video_file": "memory.mp4",
            "index_file": "memory_index.json",
            "query": "sample content",
            "top_k": 5
        }
        results = MemvidAdapter.from_obj(Document, search_config, many=True)
        ```
    """

    obj_key = "memvid"

    @classmethod
    def _import_memvid(cls):
        """Import memvid with proper error handling."""
        try:
            from memvid import MemvidEncoder, MemvidRetriever

            return MemvidEncoder, MemvidRetriever
        except ImportError as e:
            raise ConnectionError.from_adapter(
                cls,
                "Failed to import memvid",
                install_hint="pip install memvid",
                cause=e,
            )

    # outgoing - build video memory from models
    @classmethod
    def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        video_file: str,
        index_file: str,
        text_field: str = "text",
        chunk_size: int = 1024,
        overlap: int = 32,
        codec: str = "h265",
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **_kw,
    ) -> dict:
        try:
            # Validate required parameters
            if not video_file:
                raise ValidationError.from_adapter(
                    cls, "Missing required parameter 'video_file'"
                )
            if not index_file:
                raise ValidationError.from_adapter(
                    cls, "Missing required parameter 'index_file'"
                )

            # Import memvid classes
            MemvidEncoder, _ = cls._import_memvid()

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"encoded_count": 0}

            # Validate text field exists
            if not hasattr(items[0], text_field):
                raise ValidationError.from_adapter(
                    cls,
                    f"Text field '{text_field}' not found in model",
                    source=adapt_dump(items[0], adapt_meth, adapt_kw),
                    text_field=text_field,
                )

            # Create encoder
            try:
                encoder = MemvidEncoder()
            except Exception as e:
                raise ConnectionError.from_adapter(
                    cls, "Failed to create MemvidEncoder", cause=e
                )

            # Add text chunks from models
            for item in items:
                text = getattr(item, text_field)
                if not isinstance(text, str):
                    raise ValidationError.from_adapter(
                        cls,
                        f"Text field '{text_field}' must be a string",
                        source=text,
                        text_field=text_field,
                    )

                try:
                    # Add text chunks to encoder
                    encoder.add_text(text, chunk_size=chunk_size, overlap=overlap)
                except Exception as e:
                    raise QueryError.from_adapter(
                        cls,
                        "Error processing text chunks",
                        text_field=text_field,
                        cause=e,
                    )

            # Build video
            try:
                stats = encoder.build_video(
                    video_file,
                    index_file,
                    codec=codec,
                    show_progress=False,
                    allow_fallback=True,
                )
            except Exception as e:
                raise QueryError.from_adapter(
                    cls,
                    "Failed to build video memory",
                    video_file=video_file,
                    index_file=index_file,
                    codec=codec,
                    cause=e,
                )

            return {
                "encoded_count": len(items),
                "video_file": video_file,
                "index_file": index_file,
                **stats,
            }
        except (ValidationError, ConnectionError, QueryError, ResourceError):
            # Let our custom errors bubble up directly
            raise
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Unexpected error in Memvid adapter", cause=e
            )

    # incoming - search video memory and return models
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ) -> T | list[T]:
        try:
            # Validate required parameters
            if "video_file" not in obj:
                raise ValidationError.from_adapter(
                    cls, "Missing required parameter 'video_file'", source=obj
                )
            if "index_file" not in obj:
                raise ValidationError.from_adapter(
                    cls, "Missing required parameter 'index_file'", source=obj
                )
            if "query" not in obj:
                raise ValidationError.from_adapter(
                    cls, "Missing required parameter 'query'", source=obj
                )

            # Import memvid classes
            _, MemvidRetriever = cls._import_memvid()

            # Create retriever
            try:
                retriever = MemvidRetriever(obj["video_file"], obj["index_file"])
            except FileNotFoundError as e:
                raise ResourceError.from_adapter(
                    cls,
                    "Video memory files not found",
                    resource=f"{obj['video_file']}, {obj['index_file']}",
                    cause=e,
                )
            except Exception as e:
                raise ConnectionError.from_adapter(
                    cls, "Failed to create MemvidRetriever", cause=e
                )

            # Execute search
            try:
                top_k = obj.get("top_k", 5)
                results = retriever.search_with_metadata(obj["query"], top_k=top_k)
            except Exception as e:
                raise QueryError.from_adapter(
                    cls,
                    "Error searching video memory",
                    query=obj["query"],
                    top_k=top_k,
                    cause=e,
                )

            # Handle empty results
            if not results:
                if many:
                    return []
                raise ResourceError.from_adapter(
                    cls,
                    "No results found for query",
                    resource=obj["video_file"],
                    query=obj["query"],
                )

            # Convert results to model instances
            instances = []
            for i, result in enumerate(results):
                text_content = result.get("text", "")

                # Try with comprehensive data first, fallback to minimal
                for model_data in [
                    {"id": str(i), "text": text_content},
                    {"text": text_content},
                ]:
                    try:
                        instance = adapt_from(
                            subj_cls, model_data, adapt_meth, adapt_kw
                        )
                        instances.append(instance)
                        break
                    except Exception as e:
                        if model_data == {"text": text_content}:  # Last attempt failed
                            raise ValidationError.from_adapter(
                                cls,
                                "Validation error converting search results",
                                cause=e,
                            )

            if many:
                return instances
            return instances[0] if instances else None
        except (ValidationError, ConnectionError, QueryError, ResourceError):
            # Let our custom errors bubble up directly
            raise
        except Exception as e:
            raise QueryError.from_adapter(
                cls, "Unexpected error in Memvid adapter", cause=e
            )
