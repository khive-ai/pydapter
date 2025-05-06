# Vector Database Tutorial with Pydapter's Qdrant Adapters

This tutorial demonstrates how to use pydapter's Qdrant adapters to seamlessly
work with vector embeddings for semantic search and similarity-based retrieval.
We'll cover both synchronous and asynchronous implementations.

## Introduction to Vector Databases

Vector databases are specialized storage systems designed for high-dimensional
vector data (embeddings) that enable efficient similarity search. They're
crucial for:

- Semantic search
- Recommendation systems
- Image similarity
- Document retrieval
- Natural language understanding

Qdrant is a powerful vector database with extensive filtering capabilities,
making it perfect for applications that need both semantic similarity and
metadata filtering.

## Prerequisites

### 1. Install Dependencies

```bash
# Create a virtual environment if you haven't already
python -m venv pydapter-demo
source pydapter-demo/bin/activate  # On Windows: pydapter-demo\Scripts\activate

# Install dependencies
pip install pydantic qdrant-client sentence-transformers numpy

# Install pydapter (if you haven't done so already)
# Either from PyPI when available:
# pip install pydapter
# Or from the repository:
git clone https://github.com/ohdearquant/pydapter.git
cd pydapter
pip install -e .
```

### 2. Set Up Qdrant

You can run Qdrant locally using Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

For testing, you can also use the in-memory mode without Docker.

## Basic Example: Synchronous Qdrant Adapter

Let's start by creating a document search system using the synchronous adapter:

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from pydapter.extras.qdrant_ import QdrantAdapter

# Load a sentence transformer model to generate embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dimensional embeddings

# Define our document model with vector embeddings
class Document(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str] = []
    embedding: List[float] = []  # Vector embedding

    def generate_embedding(self):
        """Generate embedding from the document content"""
        self.embedding = model.encode(self.content).tolist()
        return self

# Create sample documents
sample_docs = [
    Document(
        id="doc1",
        title="Introduction to Machine Learning",
        content="Machine learning is a field of artificial intelligence that uses statistical techniques to give computer systems the ability to learn from data.",
        tags=["ML", "AI", "Data Science"]
    ),
    Document(
        id="doc2",
        title="Deep Learning Fundamentals",
        content="Deep learning is a subset of machine learning that uses neural networks with many layers to analyze various factors of data.",
        tags=["Deep Learning", "Neural Networks", "AI"]
    ),
    Document(
        id="doc3",
        title="Natural Language Processing",
        content="NLP combines computational linguistics and AI to enable computers to understand, interpret, and generate human language.",
        tags=["NLP", "AI", "Linguistics"]
    ),
    Document(
        id="doc4",
        title="Computer Vision",
        content="Computer vision is a field of AI that trains computers to interpret and understand visual data from the world around us.",
        tags=["Computer Vision", "AI", "Image Processing"]
    ),
]

# Generate embeddings for each document
for doc in sample_docs:
    doc.generate_embedding()

# Store documents in Qdrant
def store_documents(documents):
    print(f"Storing {len(documents)} documents in Qdrant...")

    # Store in Qdrant using the QdrantAdapter
    result = QdrantAdapter.to_obj(
        documents,
        collection="documents",  # Collection name
        url=None,  # Use in-memory storage for this example
        many=True
    )

    print(f"Storage result: {result}")

# Search for similar documents
def search_documents(query_text, top_k=2):
    print(f"Searching for documents similar to: '{query_text}'")

    # Generate embedding for the query
    query_embedding = model.encode(query_text).tolist()

    # Search in Qdrant using the QdrantAdapter
    results = QdrantAdapter.from_obj(
        Document,
        {
            "collection": "documents",
            "query_vector": query_embedding,
            "top_k": top_k,
            "url": None  # Use in-memory storage
        },
        many=True
    )

    print(f"Found {len(results)} similar documents:")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.title}")
        print(f"   Content: {doc.content}")
        print(f"   Tags: {', '.join(doc.tags)}")
        print()

    return results

# Main function to demo the adapter
def main():
    # Store documents
    store_documents(sample_docs)

    # Perform searches
    search_documents("What is machine learning?")
    search_documents("How do computers understand language?")
    search_documents("How do computers process images?")

if __name__ == "__main__":
    main()
```

## Asynchronous Qdrant Adapter

Now let's implement the same functionality using the asynchronous adapter:

```python
import asyncio
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Load the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Define our document model
class Document(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str] = []
    embedding: List[float] = []

    def generate_embedding(self):
        self.embedding = model.encode(self.content).tolist()
        return self

# Create sample documents (same as the synchronous example)
sample_docs = [
    Document(
        id="doc1",
        title="Introduction to Machine Learning",
        content="Machine learning is a field of artificial intelligence that uses statistical techniques to give computer systems the ability to learn from data.",
        tags=["ML", "AI", "Data Science"]
    ),
    Document(
        id="doc2",
        title="Deep Learning Fundamentals",
        content="Deep learning is a subset of machine learning that uses neural networks with many layers to analyze various factors of data.",
        tags=["Deep Learning", "Neural Networks", "AI"]
    ),
    Document(
        id="doc3",
        title="Natural Language Processing",
        content="NLP combines computational linguistics and AI to enable computers to understand, interpret, and generate human language.",
        tags=["NLP", "AI", "Linguistics"]
    ),
    Document(
        id="doc4",
        title="Computer Vision",
        content="Computer vision is a field of AI that trains computers to interpret and understand visual data from the world around us.",
        tags=["Computer Vision", "AI", "Image Processing"]
    ),
]

# Generate embeddings for each document
for doc in sample_docs:
    doc.generate_embedding()

# Store documents in Qdrant asynchronously
async def store_documents(documents):
    print(f"Storing {len(documents)} documents in Qdrant...")

    # Store in Qdrant using the AsyncQdrantAdapter
    result = await AsyncQdrantAdapter.to_obj(
        documents,
        collection="documents",
        url=None,  # Use in-memory storage
        many=True
    )

    print(f"Storage result: {result}")

# Search for similar documents asynchronously
async def search_documents(query_text, top_k=2):
    print(f"Searching for documents similar to: '{query_text}'")

    # Generate embedding for the query
    query_embedding = model.encode(query_text).tolist()

    # Search in Qdrant using the AsyncQdrantAdapter
    results = await AsyncQdrantAdapter.from_obj(
        Document,
        {
            "collection": "documents",
            "query_vector": query_embedding,
            "top_k": top_k,
            "url": None
        },
        many=True
    )

    print(f"Found {len(results)} similar documents:")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.title}")
        print(f"   Content: {doc.content}")
        print(f"   Tags: {', '.join(doc.tags)}")
        print()

    return results

# Main async function
async def main():
    # Store documents
    await store_documents(sample_docs)

    # Perform searches
    await search_documents("What is machine learning?")
    await search_documents("How do computers understand language?")
    await search_documents("How do computers process images?")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Example: Semantic Product Search with Filtering

Let's build a more practical example - a product search system that combines
semantic similarity with metadata filtering:

```python
import asyncio
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Load the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Define our product model with the AsyncAdaptable mixin
class Product(BaseModel, AsyncAdaptable):
    id: str
    name: str
    description: str
    price: float
    category: str
    brand: str
    tags: List[str] = []
    embedding: List[float] = []

    def generate_embedding(self):
        # Combine name and description for better semantic search
        text = f"{self.name}. {self.description}"
        self.embedding = model.encode(text).tolist()
        return self

# Register the async Qdrant adapter
Product.register_async_adapter(AsyncQdrantAdapter)

# Sample products
sample_products = [
    Product(
        id="p1",
        name="Premium Wireless Headphones",
        description="Noise-cancelling wireless headphones with 30-hour battery life and premium sound quality.",
        price=299.99,
        category="Electronics",
        brand="SoundMaster",
        tags=["wireless", "noise-cancelling", "premium", "headphones"]
    ),
    Product(
        id="p2",
        name="Ultra-Slim Laptop",
        description="Lightweight laptop with 15-inch display, 16GB RAM, and 512GB SSD. Perfect for productivity on the go.",
        price=1299.99,
        category="Electronics",
        brand="TechPro",
        tags=["laptop", "lightweight", "powerful", "portable"]
    ),
    Product(
        id="p3",
        name="Smart Fitness Watch",
        description="Track your fitness goals with this advanced smartwatch featuring heart rate monitoring, GPS, and sleep tracking.",
        price=199.99,
        category="Wearables",
        brand="FitTech",
        tags=["fitness", "smartwatch", "health", "tracking"]
    ),
    Product(
        id="p4",
        name="Wireless Earbuds",
        description="Compact wireless earbuds with crystal clear sound, water resistance, and 24-hour battery life with the charging case.",
        price=129.99,
        category="Electronics",
        brand="SoundMaster",
        tags=["wireless", "earbuds", "compact", "waterproof"]
    ),
    Product(
        id="p5",
        name="Professional DSLR Camera",
        description="High-end DSLR camera with 24MP sensor, 4K video recording, and professional-grade image quality.",
        price=1499.99,
        category="Photography",
        brand="OptixPro",
        tags=["camera", "professional", "DSLR", "high-quality"]
    ),
]

# Generate embeddings for all products
for product in sample_products:
    product.generate_embedding()

# Product search system
class ProductSearchSystem:
    def __init__(self, collection_name="products", url=None):
        self.collection_name = collection_name
        self.url = url

    async def initialize(self, products):
        """Initialize the search system with products"""
        print(f"Initializing product search system with {len(products)} products...")

        # Store products in Qdrant
        results = []
        for product in products:
            result = await product.adapt_to_async(
                obj_key="async_qdrant",
                collection=self.collection_name,
                url=self.url
            )
            results.append(result)

        print("Product search system initialized successfully")
        return results

    async def search(self, query_text, filters=None, top_k=3):
        """Search for products by semantic similarity with optional filtering"""
        print(f"Searching for products similar to: '{query_text}'")
        if filters:
            filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
            print(f"With filters: {filter_desc}")

        # Generate embedding for the query
        query_embedding = model.encode(query_text).tolist()

        # We'll do the filtering in Python since pydapter doesn't directly expose Qdrant's filtering
        # In a real implementation, you could extend the adapter to support Qdrant's filtering

        # First, search by vector similarity
        results = await Product.adapt_from_async(
            {
                "collection": self.collection_name,
                "query_vector": query_embedding,
                "top_k": top_k * 3 if filters else top_k,  # Get more results to allow for filtering
                "url": self.url
            },
            obj_key="async_qdrant",
            many=True
        )

        # Apply filters if specified
        if filters:
            filtered_results = []
            for product in results:
                match = True
                for key, value in filters.items():
                    if hasattr(product, key):
                        if isinstance(value, list):
                            # For list values (e.g., checking if a tag is in tags)
                            if isinstance(getattr(product, key), list):
                                if not any(v in getattr(product, key) for v in value):
                                    match = False
                                    break
                        else:
                            # For exact value matching
                            if getattr(product, key) != value:
                                match = False
                                break
                if match:
                    filtered_results.append(product)

            # Limit to top_k after filtering
            results = filtered_results[:top_k]

        print(f"Found {len(results)} matching products:")
        for i, product in enumerate(results):
            print(f"{i+1}. {product.name} - ${product.price}")
            print(f"   Brand: {product.brand}, Category: {product.category}")
            print(f"   Description: {product.description}")
            print(f"   Tags: {', '.join(product.tags)}")
            print()

        return results

# Main function to demo the advanced search system
async def main():
    # Create and initialize the search system
    search_system = ProductSearchSystem()
    await search_system.initialize(sample_products)

    # Perform various searches
    print("\n--- Basic Semantic Search ---")
    await search_system.search("wireless audio devices")

    print("\n--- Search with Brand Filter ---")
    await search_system.search("wireless audio", filters={"brand": "SoundMaster"})

    print("\n--- Search with Price Filter ---")
    await search_system.search("portable computing device", filters={"category": "Electronics"})

    print("\n--- Search with Tag Filter ---")
    await search_system.search("advanced technology", filters={"tags": ["professional", "powerful"]})

if __name__ == "__main__":
    asyncio.run(main())
```

## Working with a Persistent Qdrant Instance

For production use, you'll want to connect to a persistent Qdrant instance
rather than using in-memory storage. Here's how to do it:

```python
import asyncio
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Define model and transformer as before
model = SentenceTransformer('all-MiniLM-L6-v2')

class Document(BaseModel):
    id: str
    title: str
    content: str
    embedding: List[float] = []

    def generate_embedding(self):
        self.embedding = model.encode(self.content).tolist()
        return self

async def demo_persistent_qdrant():
    # Connect to Qdrant running in Docker
    qdrant_url = "http://localhost:6333"

    # Create a test document
    doc = Document(
        id="test1",
        title="Test Document",
        content="This is a test document to verify connection to a persistent Qdrant instance."
    ).generate_embedding()

    try:
        # Store the document
        print("Storing document in persistent Qdrant...")
        result = await AsyncQdrantAdapter.to_obj(
            doc,
            collection="test_collection",
            url=qdrant_url
        )
        print(f"Storage result: {result}")

        # Search for the document
        print("\nRetrieving document from persistent Qdrant...")
        query_embedding = model.encode("test document verify").tolist()
        results = await AsyncQdrantAdapter.from_obj(
            Document,
            {
                "collection": "test_collection",
                "query_vector": query_embedding,
                "url": qdrant_url
            },
            many=True
        )

        print(f"Retrieved {len(results)} documents:")
        for doc in results:
            print(f"  - {doc.title}: {doc.content}")

    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        print("Make sure Qdrant is running on localhost:6333")

if __name__ == "__main__":
    asyncio.run(demo_persistent_qdrant())
```

## Error Handling for Vector Operations

Let's demonstrate proper error handling for common Qdrant operations:

```python
import asyncio
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
from pydapter.exceptions import ConnectionError, QueryError, ResourceError, ValidationError
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Define a simple model
class ImageVector(BaseModel):
    id: str
    embedding: List[float]

async def handle_vector_errors():
    print("Testing error handling for vector operations...")

    # 1. Validation error - empty vector
    try:
        invalid_vector = ImageVector(id="test1", embedding=[])
        await AsyncQdrantAdapter.to_obj(
            invalid_vector,
            collection="test_collection",
            url=None
        )
    except ValidationError as e:
        print(f"Vector validation error handled: {e}")

    # 2. Validation error - inconsistent vector dimensions
    try:
        # First create a collection with 5D vectors
        valid_vector = ImageVector(id="test2", embedding=[0.1, 0.2, 0.3, 0.4, 0.5])
        await AsyncQdrantAdapter.to_obj(
            valid_vector,
            collection="dimension_test",
            url=None
        )

        # Then try to add a 3D vector to the same collection
        invalid_vector = ImageVector(id="test3", embedding=[0.1, 0.2, 0.3])
        await AsyncQdrantAdapter.to_obj(
            invalid_vector,
            collection="dimension_test",
            url=None
        )
    except ValidationError as e:
        print(f"Vector dimension mismatch handled: {e}")

    # 3. Connection error - wrong URL
    try:
        vector = ImageVector(id="test4", embedding=[0.1, 0.2, 0.3, 0.4, 0.5])
        await AsyncQdrantAdapter.to_obj(
            vector,
            collection="test_collection",
            url="http://nonexistent-qdrant-host:6333"
        )
    except ConnectionError as e:
        print(f"Connection error handled: {e}")

    # 4. Resource error - collection doesn't exist
    try:
        await AsyncQdrantAdapter.from_obj(
            ImageVector,
            {
                "collection": "nonexistent_collection",
                "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                "url": None
            }
        )
    except ResourceError as e:
        print(f"Resource error handled: {e}")

if __name__ == "__main__":
    asyncio.run(handle_vector_errors())
```

## Advanced Topics: Working with High-Dimensional Vectors

For production applications, you'll often work with higher-dimensional vectors.
Here's how to use pydapter with larger models:

```python
import asyncio
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Load a larger model with higher dimensions
# ada-002 generates 1536-dimensional vectors, better for semantic similarity
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')  # 768 dimensions

class Document(BaseModel):
    id: str
    title: str
    content: str
    embedding: List[float] = []

    def generate_embedding(self):
        self.embedding = model.encode(self.content).tolist()
        return self

async def demo_high_dim_vectors():
    print("Demonstrating high-dimensional vector operations...")

    # Create a document with high-dim embedding
    doc = Document(
        id="highdim1",
        title="High-Dimensional Vector Example",
        content="This document has a higher-dimensional embedding vector for better semantic search accuracy."
    ).generate_embedding()

    print(f"Generated embedding with {len(doc.embedding)} dimensions")

    # Store in Qdrant
    print("Storing document...")
    result = await AsyncQdrantAdapter.to_obj(
        doc,
        collection="highdim_documents",
        url=None
    )

    # Search with a similar query
    query_text = "semantic search with high dimensions"
    print(f"Searching with query: '{query_text}'")

    query_embedding = model.encode(query_text).tolist()
    results = await AsyncQdrantAdapter.from_obj(
        Document,
        {
            "collection": "highdim_documents",
            "query_vector": query_embedding,
            "url": None
        },
        many=True
    )

    print(f"Found {len(results)} results:")
    for doc in results:
        print(f"  - {doc.title}: {doc.content}")

if __name__ == "__main__":
    asyncio.run(demo_high_dim_vectors())
```

## Real-World Application: Document Search Engine

Let's build a more complete document search engine with pydapter and Qdrant:

```python
import asyncio
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

# Load the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

class Document(BaseModel, AsyncAdaptable):
    id: str
    title: str
    content: str
    author: Optional[str] = None
    date: Optional[str] = None
    source: Optional[str] = None
    tags: List[str] = []
    embedding: List[float] = []

    def generate_embedding(self):
        # Combine title and content for better semantic search
        text = f"{self.title}. {self.content}"
        self.embedding = model.encode(text).tolist()
        return self

# Register the async Qdrant adapter
Document.register_async_adapter(AsyncQdrantAdapter)

class DocumentSearchEngine:
    def __init__(self, collection_name="documents", url=None):
        self.collection_name = collection_name
        self.url = url

    async def add_document(self, document):
        """Add a single document to the search engine"""
        # Generate embedding if not already present
        if not document.embedding:
            document.generate_embedding()

        # Store in Qdrant
        result = await document.adapt_to_async(
            obj_key="async_qdrant",
            collection=self.collection_name,
            url=self.url
        )

        return result

    async def add_documents(self, documents):
        """Add multiple documents to the search engine"""
        results = []
        for doc in documents:
            result = await self.add_document(doc)
            results.append(result)

        return results

    async def search(self, query_text, filters=None, top_k=5):
        """Search for documents similar to the query text with optional filters"""
        # Generate embedding for the query
        query_embedding = model.encode(query_text).tolist()

        # Get raw results (we'll filter in Python)
        raw_results = await Document.adapt_from_async(
            {
                "collection": self.collection_name,
                "query_vector": query_embedding,
                "top_k": top_k * 3 if filters else top_k,  # Get more results when filtering
                "url": self.url
            },
            obj_key="async_qdrant",
            many=True
        )

        # Apply filters if any
        if filters:
            filtered_results = []
            for doc in raw_results:
                match = True
                for key, value in filters.items():
                    if hasattr(doc, key):
                        if isinstance(value, list):
                            # For tags or other list fields
                            if isinstance(getattr(doc, key), list):
                                if not any(v in getattr(doc, key) for v in value):
                                    match = False
                                    break
                        elif key == "date" and isinstance(value, dict):
                            # Special handling for date range filters
                            doc_date = getattr(doc, key)
                            if not doc_date:
                                match = False
                                break

                            if "from" in value and doc_date < value["from"]:
                                match = False
                                break

                            if "to" in value and doc_date > value["to"]:
                                match = False
                                break
                        else:
                            # For exact matching
                            if getattr(doc, key) != value:
                                match = False
                                break

                if match:
                    filtered_results.append(doc)

            # Limit to top_k after filtering
            results = filtered_results[:top_k]
        else:
            results = raw_results[:top_k]

        return results

    async def get_document(self, doc_id):
        """Retrieve a specific document by ID"""
        # In a real implementation, you would use Qdrant's point_id search
        # For now, we'll use the vector search and filter in Python
        try:
            # Get a document with a similar ID (not ideal, but works for the example)
            results = await Document.adapt_from_async(
                {
                    "collection": self.collection_name,
                    "query_vector": model.encode(doc_id).tolist(),
                    "top_k": 10,
                    "url": self.url
                },
                obj_key="async_qdrant",
                many=True
            )

            # Find the exact ID match
            for doc in results:
                if doc.id == doc_id:
                    return doc

            return None
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None

    async def delete_document(self, doc_id):
        """Delete a document by ID"""
        # This functionality would require extending the adapter
        # to support Qdrant's delete_points method
        raise NotImplementedError("Delete functionality not yet implemented")

async def main():
    # Create sample documents
    documents = [
        Document(
            id="doc1",
            title="Introduction to Vector Databases",
            content="Vector databases store high-dimensional vectors and enable semantic search based on similarity rather than exact matching.",
            author="Jane Smith",
            date="2023-01-15",
            source="TechBlog",
            tags=["vector-database", "semantic-search", "embeddings"]
        ),
        Document(
            id="doc2",
            title="Machine Learning Fundamentals",
            content="Machine learning algorithms learn patterns from data without being explicitly programmed. They improve with experience.",
            author="John Doe",
            date="2023-02-20",
            source="AI Journal",
            tags=["machine-learning", "AI", "algorithms"]
        ),
        Document(
            id="doc3",
            title="Natural Language Processing Techniques",
            content="NLP enables computers to understand human language by processing, analyzing, and generating text data.",
            author="Jane Smith",
            date="2023-03-10",
            source="AI Journal",
            tags=["NLP", "text-processing", "AI"]
        ),
        Document(
            id="doc4",
            title="Semantic Search Implementation",
            content="Implementing semantic search requires converting text to vector embeddings and finding similar vectors efficiently.",
            author="Alex Johnson",
            date="2023-04-05",
            source="TechBlog",
            tags=["semantic-search", "embeddings", "implementation"]
        ),
        Document(
            id="doc5",
            title="Vector Database Comparison",
            content="Comparing popular vector databases like Qdrant, Pinecone, and Milvus for semantic search applications.",
            author="Chris Williams",
            date="2023-05-12",
            source="Database Review",
            tags=["vector-database", "comparison", "Qdrant", "Pinecone", "Milvus"]
        ),
    ]

    # Initialize the search engine
    search_engine = DocumentSearchEngine()

    # Add sample documents
    print("Adding sample documents to the search engine...")
    await search_engine.add_documents(documents)

    # Perform searches
    print("\n--- Basic Semantic Search ---")
    results = await search_engine.search("How do vector databases work?")
    print(f"Found {len(results)} documents:")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.title}")
        print(f"   Author: {doc.author}, Date: {doc.date}")
        print(f"   Content: {doc.content}")
        print()

    print("\n--- Search with Author Filter ---")
    author_results = await search_engine.search(
        "AI and machine learning techniques",
        filters={"author": "Jane Smith"}
    )
    print(f"Found {len(author_results)} documents by Jane Smith:")
    for i, doc in enumerate(author_results):
        print(f"{i+1}. {doc.title}")
        print(f"   Author: {doc.author}, Date: {doc.date}")
        print(f"   Content: {doc.content}")
        print()

    print("\n--- Search with Tag Filter ---")
    tag_results = await search_engine.search(
        "database technology",
        filters={"tags": ["vector-database"]}
    )
    print(f"Found {len(tag_results)} documents with 'vector-database' tag:")
    for i, doc in enumerate(tag_results):
        print(f"{i+1}. {doc.title}")
        print(f"   Tags: {', '.join(doc.tags)}")
        print(f"   Content: {doc.content}")
        print()

    print("\n--- Get Document by ID ---")
    doc = await search_engine.get_document("doc3")
    if doc:
        print(f"Retrieved document: {doc.title}")
        print(f"Content: {doc.content}")
    else:
        print("Document not found")

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusion

In this tutorial, you've learned how to use pydapter's Qdrant adapters to build
semantic search applications with vector embeddings. We've covered:

1. Setting up Qdrant and generating vector embeddings
2. Using both synchronous and asynchronous adapters
3. Storing Pydantic models with embeddings in Qdrant
4. Performing similarity searches
5. Implementing filtering and advanced search features
6. Building complete search applications

Vector databases like Qdrant are powerful tools for implementing semantic
search, recommendation systems, and other AI applications that require
similarity matching rather than exact keyword matching.

The pydapter adapters make it easy to integrate vector database functionality
into your Python applications, with a clean and consistent interface for working
with Pydantic models.

By combining pydapter's adapters with pre-trained embedding models like
sentence-transformers, you can quickly build sophisticated semantic search
systems with minimal code.
