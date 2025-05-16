# Tutorial: Using Protocols to Create Standardized Models

This tutorial demonstrates how to use the pydapter protocols module to create
models with standardized capabilities. We'll build a simple document management
system that leverages the protocol interfaces to provide consistent behavior
across different types of documents.

## Prerequisites

Before starting, ensure you have installed pydapter with the protocols
extension:

```bash
pip install pydapter[protocols]
```

## Step 1: Define Base Document Models

First, let's define our base document models using the protocols:

```python
from datetime import datetime
from uuid import UUID

from pydapter.protocols import Identifiable, Temporal, Embedable

class BaseDocument(Identifiable, Temporal):
    """Base document class with ID and timestamp tracking."""

    title: str
    author: str

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"


class EmbeddableDocument(BaseDocument, Embedable):
    """Document that supports vector embeddings."""

    content: str

    def create_content(self) -> str:
        """Create content for embedding from document metadata and content."""
        return f"{self.title}\n{self.author}\n{self.content}"
```

## Step 2: Create Specific Document Types

Now, let's create specific document types that inherit from our base classes:

```python
class TextDocument(EmbeddableDocument):
    """A simple text document."""

    format: str = "text"


class PDFDocument(EmbeddableDocument):
    """A PDF document with additional metadata."""

    format: str = "pdf"
    page_count: int


class ImageDocument(BaseDocument):
    """An image document that doesn't need text embedding."""

    format: str = "image"
    width: int
    height: int
    file_path: str
```

## Step 3: Create a Document Repository

Let's create a simple repository to manage our documents:

```python
from typing import Dict, List, Optional, Type, TypeVar

T = TypeVar('T', bound=BaseDocument)

class DocumentRepository:
    """Repository for managing documents."""

    def __init__(self):
        self.documents: Dict[UUID, BaseDocument] = {}

    def add(self, document: BaseDocument) -> None:
        """Add a document to the repository."""
        self.documents[document.id] = document

    def get(self, document_id: UUID) -> Optional[BaseDocument]:
        """Get a document by ID."""
        return self.documents.get(document_id)

    def list_all(self) -> List[BaseDocument]:
        """List all documents."""
        return list(self.documents.values())

    def find_by_type(self, doc_type: Type[T]) -> List[T]:
        """Find documents by type."""
        return [doc for doc in self.documents.values() if isinstance(doc, doc_type)]

    def find_by_author(self, author: str) -> List[BaseDocument]:
        """Find documents by author."""
        return [doc for doc in self.documents.values() if doc.author == author]

    def update(self, document: BaseDocument) -> None:
        """Update a document."""
        if document.id in self.documents:
            # Update the timestamp
            document.update_timestamp()
            self.documents[document.id] = document
```

## Step 4: Working with Documents

Now let's use our document models and repository:

```python
# Create a repository
repo = DocumentRepository()

# Create some documents
text_doc = TextDocument(
    title="Getting Started with Protocols",
    author="Jane Smith",
    content="This document explains how to use protocols effectively."
)

pdf_doc = PDFDocument(
    title="Advanced Protocol Patterns",
    author="John Doe",
    content="Detailed explanation of advanced protocol usage patterns.",
    page_count=42
)

image_doc = ImageDocument(
    title="Protocol Architecture Diagram",
    author="Jane Smith",
    width=1920,
    height=1080,
    file_path="/images/protocol_diagram.png"
)

# Add documents to the repository
repo.add(text_doc)
repo.add(pdf_doc)
repo.add(image_doc)

# List all documents
print("All documents:")
for doc in repo.list_all():
    print(f"- {doc}")

# Find documents by author
print("\nDocuments by Jane Smith:")
for doc in repo.find_by_author("Jane Smith"):
    print(f"- {doc}")

# Find documents by type
print("\nText documents:")
for doc in repo.find_by_type(TextDocument):
    print(f"- {doc}")

# Update a document
text_doc.title = "Updated: Getting Started with Protocols"
repo.update(text_doc)
print(f"\nUpdated document timestamp: {text_doc.updated_at}")
```

## Step 5: Working with Embeddings

Let's extend our example to work with embeddings:

```python
import numpy as np
from typing import List, Tuple

def generate_mock_embedding(text: str) -> List[float]:
    """Generate a mock embedding for demonstration purposes."""
    # In a real application, you would use a proper embedding model
    # This is just a simple hash-based approach for demonstration
    np_array = np.array([ord(c) for c in text], dtype=np.float32)
    return (np_array / np.linalg.norm(np_array)).tolist()[:10]  # Normalize and take first 10 dims

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot_product / (norm_a * norm_b)

# Generate embeddings for our documents
for doc in repo.find_by_type(EmbeddableDocument):
    content = doc.create_content()
    doc.embedding = generate_mock_embedding(content)
    print(f"Generated embedding for '{doc.title}' with {len(doc.embedding)} dimensions")

# Find similar documents
def find_similar_documents(
    query_doc: EmbeddableDocument,
    candidates: List[EmbeddableDocument],
    threshold: float = 0.7
) -> List[Tuple[EmbeddableDocument, float]]:
    """Find documents similar to the query document."""
    results = []
    for doc in candidates:
        if doc.id != query_doc.id:  # Skip the query document itself
            similarity = cosine_similarity(query_doc.embedding, doc.embedding)
            if similarity >= threshold:
                results.append((doc, similarity))
    return sorted(results, key=lambda x: x[1], reverse=True)

# Find documents similar to our text document
embedable_docs = repo.find_by_type(EmbeddableDocument)
similar_docs = find_similar_documents(text_doc, embedable_docs)

print("\nDocuments similar to 'Getting Started with Protocols':")
for doc, similarity in similar_docs:
    print(f"- {doc.title} (similarity: {similarity:.2f})")
```

## Step 6: Adding Event Tracking

Let's extend our system to track document events using the `Invokable` protocol:

```python
import asyncio
from pydapter.protocols import Invokable, Event
from datetime import datetime

class DocumentEvent(Event):
    """Event for tracking document operations."""

    event_type: str
    document_id: UUID
    user_id: str

    async def process(self):
        """Process the event."""
        # In a real application, this might log to a database or message queue
        print(f"Processing event: {self.event_type} for document {self.document_id}")
        return {"processed": True, "timestamp": datetime.now().isoformat()}

async def track_document_event(
    event_type: str,
    document: BaseDocument,
    user_id: str
) -> DocumentEvent:
    """Track a document event."""
    event = DocumentEvent(
        event_type=event_type,
        document_id=document.id,
        user_id=user_id,
        content=f"{event_type} operation on {document.title} by user {user_id}"
    )
    event._invoke_function = event.process
    await event.invoke()
    return event

# Example usage in an async context
async def main():
    # Track a view event
    view_event = await track_document_event("view", text_doc, "user123")
    print(f"Event status: {view_event.execution.status}")
    print(f"Event duration: {view_event.execution.duration:.6f} seconds")
    print(f"Event response: {view_event.execution.response}")

    # Track an edit event
    edit_event = await track_document_event("edit", text_doc, "user123")
    print(f"Event status: {edit_event.execution.status}")

# Run the async example
asyncio.run(main())
```

## Complete Example

Here's the complete example combining all the steps:

```python
import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from pydapter.protocols import Identifiable, Temporal, Embedable, Invokable, Event

# Step 1: Define Base Document Models
class BaseDocument(Identifiable, Temporal):
    """Base document class with ID and timestamp tracking."""

    title: str
    author: str

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"


class EmbeddableDocument(BaseDocument, Embedable):
    """Document that supports vector embeddings."""

    content: str

    def create_content(self) -> str:
        """Create content for embedding from document metadata and content."""
        return f"{self.title}\n{self.author}\n{self.content}"


# Step 2: Create Specific Document Types
class TextDocument(EmbeddableDocument):
    """A simple text document."""

    format: str = "text"


class PDFDocument(EmbeddableDocument):
    """A PDF document with additional metadata."""

    format: str = "pdf"
    page_count: int


class ImageDocument(BaseDocument):
    """An image document that doesn't need text embedding."""

    format: str = "image"
    width: int
    height: int
    file_path: str


# Step 3: Create a Document Repository
T = TypeVar('T', bound=BaseDocument)

class DocumentRepository:
    """Repository for managing documents."""

    def __init__(self):
        self.documents: Dict[UUID, BaseDocument] = {}

    def add(self, document: BaseDocument) -> None:
        """Add a document to the repository."""
        self.documents[document.id] = document

    def get(self, document_id: UUID) -> Optional[BaseDocument]:
        """Get a document by ID."""
        return self.documents.get(document_id)

    def list_all(self) -> List[BaseDocument]:
        """List all documents."""
        return list(self.documents.values())

    def find_by_type(self, doc_type: Type[T]) -> List[T]:
        """Find documents by type."""
        return [doc for doc in self.documents.values() if isinstance(doc, doc_type)]

    def find_by_author(self, author: str) -> List[BaseDocument]:
        """Find documents by author."""
        return [doc for doc in self.documents.values() if doc.author == author]

    def update(self, document: BaseDocument) -> None:
        """Update a document."""
        if document.id in self.documents:
            # Update the timestamp
            document.update_timestamp()
            self.documents[document.id] = document


# Step 6: Define Document Event
class DocumentEvent(Event):
    """Event for tracking document operations."""

    event_type: str
    document_id: UUID
    user_id: str

    async def process(self):
        """Process the event."""
        # In a real application, this might log to a database or message queue
        print(f"Processing event: {self.event_type} for document {self.document_id}")
        return {"processed": True, "timestamp": datetime.now().isoformat()}


# Helper functions
def generate_mock_embedding(text: str) -> List[float]:
    """Generate a mock embedding for demonstration purposes."""
    # In a real application, you would use a proper embedding model
    # This is just a simple hash-based approach for demonstration
    np_array = np.array([ord(c) for c in text], dtype=np.float32)
    return (np_array / np.linalg.norm(np_array)).tolist()[:10]  # Normalize and take first 10 dims


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot_product / (norm_a * norm_b)


def find_similar_documents(
    query_doc: EmbeddableDocument,
    candidates: List[EmbeddableDocument],
    threshold: float = 0.7
) -> List[Tuple[EmbeddableDocument, float]]:
    """Find documents similar to the query document."""
    results = []
    for doc in candidates:
        if doc.id != query_doc.id:  # Skip the query document itself
            similarity = cosine_similarity(query_doc.embedding, doc.embedding)
            if similarity >= threshold:
                results.append((doc, similarity))
    return sorted(results, key=lambda x: x[1], reverse=True)


async def track_document_event(
    event_type: str,
    document: BaseDocument,
    user_id: str
) -> DocumentEvent:
    """Track a document event."""
    event = DocumentEvent(
        event_type=event_type,
        document_id=document.id,
        user_id=user_id,
        content=f"{event_type} operation on {document.title} by user {user_id}"
    )
    event._invoke_function = event.process
    await event.invoke()
    return event


# Main function to demonstrate usage
async def main():
    # Create a repository
    repo = DocumentRepository()

    # Create some documents
    text_doc = TextDocument(
        title="Getting Started with Protocols",
        author="Jane Smith",
        content="This document explains how to use protocols effectively."
    )

    pdf_doc = PDFDocument(
        title="Advanced Protocol Patterns",
        author="John Doe",
        content="Detailed explanation of advanced protocol usage patterns.",
        page_count=42
    )

    image_doc = ImageDocument(
        title="Protocol Architecture Diagram",
        author="Jane Smith",
        width=1920,
        height=1080,
        file_path="/images/protocol_diagram.png"
    )

    # Add documents to the repository
    repo.add(text_doc)
    repo.add(pdf_doc)
    repo.add(image_doc)

    # List all documents
    print("All documents:")
    for doc in repo.list_all():
        print(f"- {doc}")

    # Find documents by author
    print("\nDocuments by Jane Smith:")
    for doc in repo.find_by_author("Jane Smith"):
        print(f"- {doc}")

    # Find documents by type
    print("\nText documents:")
    for doc in repo.find_by_type(TextDocument):
        print(f"- {doc}")

    # Update a document
    text_doc.title = "Updated: Getting Started with Protocols"
    repo.update(text_doc)
    print(f"\nUpdated document timestamp: {text_doc.updated_at}")

    # Generate embeddings for our documents
    for doc in repo.find_by_type(EmbeddableDocument):
        content = doc.create_content()
        doc.embedding = generate_mock_embedding(content)
        print(f"Generated embedding for '{doc.title}' with {len(doc.embedding)} dimensions")

    # Find similar documents
    embedable_docs = repo.find_by_type(EmbeddableDocument)
    similar_docs = find_similar_documents(text_doc, embedable_docs)

    print("\nDocuments similar to 'Updated: Getting Started with Protocols':")
    for doc, similarity in similar_docs:
        print(f"- {doc.title} (similarity: {similarity:.2f})")

    # Track document events
    view_event = await track_document_event("view", text_doc, "user123")
    print(f"\nEvent status: {view_event.execution.status}")
    print(f"Event duration: {view_event.execution.duration:.6f} seconds")
    print(f"Event response: {view_event.execution.response}")

    edit_event = await track_document_event("edit", text_doc, "user123")
    print(f"Event status: {edit_event.execution.status}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Summary

In this tutorial, we've demonstrated how to use pydapter's protocols to create
standardized models with consistent behavior. We've covered:

1. Creating base document models with `Identifiable` and `Temporal` protocols
2. Adding embedding support with the `Embedable` protocol
3. Building a document repository to manage our models
4. Working with document embeddings for similarity search
5. Tracking document events with the `Invokable` and `Event` protocols

The protocols module provides a powerful way to add standardized capabilities to
your models, making your code more consistent and easier to maintain.
