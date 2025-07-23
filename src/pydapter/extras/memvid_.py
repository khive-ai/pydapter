"""
Memvid adapter - uses `memvid` for video-based AI memory.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..core import Adapter
from ..exceptions import ConnectionError, QueryError, ResourceError, ValidationError

T = TypeVar("T", bound=BaseModel)


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

    @staticmethod
    def _import_memvid():
        """Import memvid with proper error handling."""
        try:
            from memvid import MemvidEncoder, MemvidRetriever

            return MemvidEncoder, MemvidRetriever
        except ImportError as e:
            raise ConnectionError(
                f"Failed to import memvid: {e}. Install with: pip install memvid",
                adapter="memvid",
            ) from e

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
        **_kw,
    ) -> dict:
        try:
            # Validate required parameters
            if not video_file:
                raise ValidationError("Missing required parameter 'video_file'")
            if not index_file:
                raise ValidationError("Missing required parameter 'index_file'")

            # Import memvid classes
            MemvidEncoder, _ = cls._import_memvid()

            # Prepare data
            items = subj if isinstance(subj, Sequence) else [subj]
            if not items:
                return {"encoded_count": 0}

            # Validate text field exists
            if not hasattr(items[0], text_field):
                raise ValidationError(
                    f"Text field '{text_field}' not found in model",
                    data=getattr(items[0], adapt_meth)(),
                )

            # Create encoder
            try:
                encoder = MemvidEncoder()
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create MemvidEncoder: {e}",
                    adapter="memvid",
                ) from e

            # Add text chunks from models
            try:
                for item in items:
                    text = getattr(item, text_field)
                    if not isinstance(text, str):
                        raise ValidationError(
                            f"Text field '{text_field}' must be a string",
                            data=text,
                        )

                    # Add text chunks to encoder
                    encoder.add_text(text, chunk_size=chunk_size, overlap=overlap)

            except ValidationError:
                raise
            except Exception as e:
                raise QueryError(
                    f"Error processing text chunks: {e}",
                    adapter="memvid",
                ) from e

            # Build video
            try:
                stats = encoder.build_video(
                    video_file,
                    index_file,
                    codec=codec,
                    show_progress=False,
                    allow_fallback=True,
                )
                return {
                    "encoded_count": len(items),
                    "video_file": video_file,
                    "index_file": index_file,
                    **stats,
                }
            except Exception as e:
                raise QueryError(
                    f"Failed to build video memory: {e}",
                    adapter="memvid",
                ) from e

        except (ConnectionError, QueryError, ValidationError):
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in Memvid adapter: {e}", adapter="memvid"
            )

    # incoming - search video memory and return models
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: dict,
        /,
        *,
        many=True,
        adapt_meth: str = "model_validate",
        **kw,
    ):
        try:
            # Validate required parameters
            if "video_file" not in obj:
                raise ValidationError(
                    "Missing required parameter 'video_file'", data=obj
                )
            if "index_file" not in obj:
                raise ValidationError(
                    "Missing required parameter 'index_file'", data=obj
                )
            if "query" not in obj:
                raise ValidationError("Missing required parameter 'query'", data=obj)

            # Import memvid classes
            _, MemvidRetriever = cls._import_memvid()

            # Create retriever
            try:
                retriever = MemvidRetriever(obj["video_file"], obj["index_file"])
            except FileNotFoundError as e:
                raise ResourceError(
                    f"Video memory files not found: {e}",
                    resource=f"{obj['video_file']}, {obj['index_file']}",
                ) from e
            except Exception as e:
                raise ConnectionError(
                    f"Failed to create MemvidRetriever: {e}",
                    adapter="memvid",
                ) from e

            # Execute search
            try:
                top_k = obj.get("top_k", 5)
                results = retriever.search_with_metadata(obj["query"], top_k=top_k)
            except Exception as e:
                raise QueryError(
                    f"Error searching video memory: {e}",
                    query=obj["query"],
                    adapter="memvid",
                ) from e

            # Handle empty results
            if not results:
                if many:
                    return []
                raise ResourceError(
                    "No results found for query",
                    resource=obj["video_file"],
                    query=obj["query"],
                )

            # Convert results to model instances
            try:
                # Results from memvid contain text and metadata
                # We need to create model instances from the text chunks
                # Since we don't have the original model structure, we'll create
                # minimal models with the retrieved text
                instances = []
                for i, result in enumerate(results):
                    # Try to create model with text content
                    text_content = result.get("text", "")

                    # Create a basic model instance
                    # This assumes the model has at least an id and text field
                    try:
                        # Try to extract any available metadata
                        model_data = {
                            "id": str(i),  # Use index as fallback ID
                            "text": text_content,
                        }

                        # Add any additional fields that match the model
                        instance = getattr(subj_cls, adapt_meth)(model_data)
                        instances.append(instance)
                    except PydanticValidationError:
                        # If strict validation fails, try with just the text
                        # This is a fallback for models with different structures
                        minimal_data = {"text": text_content}
                        instance = getattr(subj_cls, adapt_meth)(minimal_data)
                        instances.append(instance)

                if many:
                    return instances
                return instances[0] if instances else None

            except PydanticValidationError as e:
                raise ValidationError(
                    f"Validation error converting search results: {e}",
                    data=results[0] if results else None,
                ) from e

        except (ConnectionError, QueryError, ResourceError, ValidationError):
            raise
        except Exception as e:
            raise QueryError(
                f"Unexpected error in Memvid adapter: {e}", adapter="memvid"
            )
