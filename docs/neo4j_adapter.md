# Neo4j Adapter Tutorial for Pydapter

This tutorial will show you how to use pydapter's Neo4j adapter to seamlessly
convert between Pydantic models and Neo4j graph databases. You'll learn how to
model, store, and query graph data using Pydantic's validation capabilities.

## Prerequisites

### 1. Install Dependencies

```bash
# Create a virtual environment if you haven't already
python -m venv pydapter-demo
source pydapter-demo/bin/activate  # On Windows: pydapter-demo\Scripts\activate

# Install dependencies
pip install pydantic neo4j

# Install pydapter (if you haven't done so already)
# Either from PyPI when available:
# pip install pydapter
# Or from the repository:
git clone https://github.com/ohdearquant/pydapter.git
cd pydapter
pip install -e .
```

### 2. Set Up Neo4j

The easiest way to set up Neo4j is using Docker:

```bash
# Run Neo4j in Docker with a password
docker run \
    --name neo4j-pydapter \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password \
    -d neo4j:latest
```

Alternatively, you can:

- Download and install Neo4j Desktop from
  [Neo4j's website](https://neo4j.com/download/)
- Use Neo4j AuraDB cloud service
- Install Neo4j directly on your system

With Docker, you can access:

- Neo4j Browser UI at http://localhost:7474
- Bolt protocol at bolt://localhost:7687

## Basic Example: Person Management System

Let's build a simple person management system using Neo4j and pydapter:

```python
from pydantic import BaseModel
from typing import List, Optional
from pydapter.extras.neo4j_ import Neo4jAdapter

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")  # Default credentials, change if different

# Define a Pydantic model
class Person(BaseModel):
    id: str
    name: str
    age: int
    email: Optional[str] = None
    interests: List[str] = []

# Create some test data
people = [
    Person(id="p1", name="Alice", age=30, email="alice@example.com", interests=["coding", "hiking"]),
    Person(id="p2", name="Bob", age=25, email="bob@example.com", interests=["gaming", "cooking"]),
    Person(id="p3", name="Charlie", age=35, email="charlie@example.com", interests=["reading", "travel"])
]

# Store data in Neo4j
def store_people(people_list):
    print(f"Storing {len(people_list)} people in Neo4j...")

    for person in people_list:
        result = Neo4jAdapter.to_obj(
            person,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Person",  # Node label in Neo4j
            merge_on="id"    # Property to use for MERGE operation
        )
        print(f"Stored {person.name}: {result}")

# Retrieve all people
def get_all_people():
    print("Retrieving all people from Neo4j...")

    people = Neo4jAdapter.from_obj(
        Person,
        {
            "url": NEO4J_URI,
            "auth": NEO4J_AUTH,
            "label": "Person"
        },
        many=True
    )

    print(f"Found {len(people)} people:")
    for person in people:
        print(f"  - {person.name} (Age: {person.age}, Email: {person.email})")
        if person.interests:
            print(f"    Interests: {', '.join(person.interests)}")

    return people

# Find people by property
def find_people_by_property(property_name, property_value):
    print(f"Finding people with {property_name}={property_value}...")

    where_clause = f"n.{property_name} = '{property_value}'"

    people = Neo4jAdapter.from_obj(
        Person,
        {
            "url": NEO4J_URI,
            "auth": NEO4J_AUTH,
            "label": "Person",
            "where": where_clause
        },
        many=True
    )

    print(f"Found {len(people)} matching people:")
    for person in people:
        print(f"  - {person.name} (Age: {person.age}, Email: {person.email})")

    return people

# Main function to demo the adapter
def main():
    # First, store people
    store_people(people)

    # Retrieve all people
    all_people = get_all_people()

    # Find people with specific properties
    young_people = find_people_by_property("age", "25")

    # Find by email domain (using ENDS WITH in Cypher)
    print("\nFinding people with example.com email addresses...")
    example_emails = Neo4jAdapter.from_obj(
        Person,
        {
            "url": NEO4J_URI,
            "auth": NEO4J_AUTH,
            "label": "Person",
            "where": "n.email ENDS WITH 'example.com'"
        },
        many=True
    )

    print(f"Found {len(example_emails)} people with example.com emails:")
    for person in example_emails:
        print(f"  - {person.name}: {person.email}")

if __name__ == "__main__":
    main()
```

## Working with Relationships

One of Neo4j's key features is its ability to model relationships between nodes.
Let's expand our example to include relationships:

```python
from pydantic import BaseModel
from typing import List, Optional
from pydapter.extras.neo4j_ import Neo4jAdapter
from neo4j import GraphDatabase

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# Define models
class Person(BaseModel):
    id: str
    name: str
    age: int
    email: Optional[str] = None

class Hobby(BaseModel):
    id: str
    name: str
    category: Optional[str] = None

# Custom function to create relationships
# (Since pydapter doesn't directly handle relationships yet)
def create_relationship(person_id, hobby_id, relationship_type="ENJOYS"):
    """Create a relationship between a Person and a Hobby"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (p:Person {{id: $person_id}})
            MATCH (h:Hobby {{id: $hobby_id}})
            MERGE (p)-[r:{relationship_type}]->(h)
            RETURN p.name, h.name
            """,
            person_id=person_id,
            hobby_id=hobby_id
        )

        for record in result:
            print(f"Created relationship: {record['p.name']} {relationship_type} {record['h.name']}")

    driver.close()

# Function to find people who enjoy a specific hobby
def find_people_by_hobby(hobby_name):
    """Find all people who enjoy a specific hobby"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    people_list = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person)-[:ENJOYS]->(h:Hobby {name: $hobby_name})
            RETURN p
            """,
            hobby_name=hobby_name
        )

        for record in result:
            # Convert Neo4j node properties to dict
            person_data = dict(record["p"].items())
            # Create Pydantic model from data
            person = Person(**person_data)
            people_list.append(person)

    driver.close()
    return people_list

# Function to find hobbies for a specific person
def find_hobbies_for_person(person_id):
    """Find all hobbies for a specific person"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    hobbies_list = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {id: $person_id})-[:ENJOYS]->(h:Hobby)
            RETURN h
            """,
            person_id=person_id
        )

        for record in result:
            hobby_data = dict(record["h"].items())
            hobby = Hobby(**hobby_data)
            hobbies_list.append(hobby)

    driver.close()
    return hobbies_list

# Main function to demo relationships
def main():
    # Create people
    people = [
        Person(id="p1", name="Alice", age=30, email="alice@example.com"),
        Person(id="p2", name="Bob", age=25, email="bob@example.com"),
        Person(id="p3", name="Charlie", age=35, email="charlie@example.com")
    ]

    # Create hobbies
    hobbies = [
        Hobby(id="h1", name="Coding", category="Technical"),
        Hobby(id="h2", name="Hiking", category="Outdoor"),
        Hobby(id="h3", name="Reading", category="Indoor"),
        Hobby(id="h4", name="Cooking", category="Indoor"),
        Hobby(id="h5", name="Gaming", category="Entertainment")
    ]

    # Store people in Neo4j
    print("Storing people...")
    for person in people:
        Neo4jAdapter.to_obj(
            person,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Person",
            merge_on="id"
        )

    # Store hobbies in Neo4j
    print("\nStoring hobbies...")
    for hobby in hobbies:
        Neo4jAdapter.to_obj(
            hobby,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Hobby",
            merge_on="id"
        )

    # Create relationships
    print("\nCreating relationships...")
    # Alice enjoys Coding, Hiking, and Reading
    create_relationship("p1", "h1")
    create_relationship("p1", "h2")
    create_relationship("p1", "h3")

    # Bob enjoys Gaming and Cooking
    create_relationship("p2", "h4")
    create_relationship("p2", "h5")

    # Charlie enjoys Reading and Hiking
    create_relationship("p3", "h2")
    create_relationship("p3", "h3")

    # Find people who enjoy Hiking
    print("\nPeople who enjoy Hiking:")
    hikers = find_people_by_hobby("Hiking")
    for person in hikers:
        print(f"  - {person.name} (Age: {person.age})")

    # Find hobbies for Alice
    print("\nAlice's hobbies:")
    alice_hobbies = find_hobbies_for_person("p1")
    for hobby in alice_hobbies:
        print(f"  - {hobby.name} (Category: {hobby.category})")

if __name__ == "__main__":
    main()
```

## Advanced Example: Movie Recommendation System

Let's build a more complex example - a movie recommendation system that
demonstrates advanced Neo4j features and pydapter integration:

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pydapter.extras.neo4j_ import Neo4jAdapter
from neo4j import GraphDatabase
import random

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# Define our models
class Person(BaseModel):
    id: str
    name: str
    age: Optional[int] = None

class Movie(BaseModel):
    id: str
    title: str
    year: int
    genre: List[str] = []
    rating: Optional[float] = None

class Actor(Person):
    roles: List[str] = []

class Director(Person):
    movies_directed: int = 0

# Helper function to create Neo4j driver
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# Initialize the database with schema and constraints
def initialize_database():
    driver = get_driver()

    with driver.session() as session:
        # Create constraints to ensure uniqueness
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Movie) REQUIRE m.id IS UNIQUE")

    driver.close()
    print("Database initialized with constraints")

# Helper function to create relationships
def create_relationship(start_id, end_id, start_label, end_label, rel_type, properties=None):
    driver = get_driver()

    props_str = ""
    if properties:
        props_list = [f"{k}: ${k}" for k in properties.keys()]
        props_str = "{" + ", ".join(props_list) + "}"

    with driver.session() as session:
        query = f"""
        MATCH (a:{start_label} {{id: $start_id}})
        MATCH (b:{end_label} {{id: $end_id}})
        MERGE (a)-[r:{rel_type} {props_str}]->(b)
        RETURN a.name, b.title
        """

        params = {"start_id": start_id, "end_id": end_id}
        if properties:
            params.update(properties)

        result = session.run(query, params)
        data = result.single()
        if data:
            print(f"Created relationship: {data[0]} {rel_type} {data[1]}")

    driver.close()

# Populate the database with sample data
def populate_database():
    # Create some movies
    movies = [
        Movie(id="m1", title="The Matrix", year=1999,
              genre=["Sci-Fi", "Action"], rating=8.7),
        Movie(id="m2", title="Inception", year=2010,
              genre=["Sci-Fi", "Action", "Thriller"], rating=8.8),
        Movie(id="m3", title="The Shawshank Redemption", year=1994,
              genre=["Drama"], rating=9.3),
        Movie(id="m4", title="Pulp Fiction", year=1994,
              genre=["Crime", "Drama"], rating=8.9),
        Movie(id="m5", title="The Dark Knight", year=2008,
              genre=["Action", "Crime", "Drama"], rating=9.0),
    ]

    # Create some actors
    actors = [
        Actor(id="a1", name="Keanu Reeves", age=57, roles=["Neo", "John Wick"]),
        Actor(id="a2", name="Leonardo DiCaprio", age=46, roles=["Dom Cobb", "Jack Dawson"]),
        Actor(id="a3", name="Morgan Freeman", age=84, roles=["Ellis Boyd 'Red' Redding"]),
        Actor(id="a4", name="Tim Robbins", age=62, roles=["Andy Dufresne"]),
        Actor(id="a5", name="John Travolta", age=67, roles=["Vincent Vega"]),
        Actor(id="a6", name="Samuel L. Jackson", age=72, roles=["Jules Winnfield"]),
        Actor(id="a7", name="Christian Bale", age=47, roles=["Bruce Wayne"]),
    ]

    # Create some directors
    directors = [
        Director(id="d1", name="Lana Wachowski", age=56, movies_directed=5),
        Director(id="d2", name="Christopher Nolan", age=51, movies_directed=11),
        Director(id="d3", name="Frank Darabont", age=62, movies_directed=4),
        Director(id="d4", name="Quentin Tarantino", age=58, movies_directed=9),
    ]

    # Store movies in Neo4j
    print("Storing movies...")
    for movie in movies:
        Neo4jAdapter.to_obj(
            movie,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Movie",
            merge_on="id"
        )

    # Store actors in Neo4j
    print("\nStoring actors...")
    for actor in actors:
        # Convert to dict and add label
        actor_dict = actor.model_dump()

        # Store using Neo4jAdapter
        Neo4jAdapter.to_obj(
            actor,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Actor",  # Use Actor label
            merge_on="id"
        )

    # Store directors in Neo4j
    print("\nStoring directors...")
    for director in directors:
        Neo4jAdapter.to_obj(
            director,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Director",  # Use Director label
            merge_on="id"
        )

    # Create relationships
    print("\nCreating relationships...")

    # Matrix relationships
    create_relationship("a1", "m1", "Actor", "Movie", "ACTED_IN", {"role": "Neo"})
    create_relationship("d1", "m1", "Director", "Movie", "DIRECTED")

    # Inception relationships
    create_relationship("a2", "m2", "Actor", "Movie", "ACTED_IN", {"role": "Dom Cobb"})
    create_relationship("d2", "m2", "Director", "Movie", "DIRECTED")

    # Shawshank Redemption relationships
    create_relationship("a3", "m3", "Actor", "Movie", "ACTED_IN", {"role": "Ellis Boyd 'Red' Redding"})
    create_relationship("a4", "m3", "Actor", "Movie", "ACTED_IN", {"role": "Andy Dufresne"})
    create_relationship("d3", "m3", "Director", "Movie", "DIRECTED")

    # Pulp Fiction relationships
    create_relationship("a5", "m4", "Actor", "Movie", "ACTED_IN", {"role": "Vincent Vega"})
    create_relationship("a6", "m4", "Actor", "Movie", "ACTED_IN", {"role": "Jules Winnfield"})
    create_relationship("d4", "m4", "Director", "Movie", "DIRECTED")

    # Dark Knight relationships
    create_relationship("a7", "m5", "Actor", "Movie", "ACTED_IN", {"role": "Bruce Wayne"})
    create_relationship("d2", "m5", "Director", "Movie", "DIRECTED")

    # Create user ratings
    create_user_ratings()

    print("Database populated with sample data")

# Create some users and their ratings
def create_user_ratings():
    # Create users
    users = [
        Person(id="u1", name="User One", age=25),
        Person(id="u2", name="User Two", age=35),
        Person(id="u3", name="User Three", age=45),
    ]

    # Store users
    print("\nStoring users...")
    for user in users:
        Neo4jAdapter.to_obj(
            user,
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="User",
            merge_on="id"
        )

    # Create rating relationships
    driver = get_driver()

    with driver.session() as session:
        # Get all movie IDs
        result = session.run("MATCH (m:Movie) RETURN m.id AS id")
        movie_ids = [record["id"] for record in result]

        # For each user, create some random ratings
        for user_id in ["u1", "u2", "u3"]:
            for movie_id in movie_ids:
                # Randomly decide if user rated this movie
                if random.random() > 0.3:  # 70% chance of rating
                    rating = round(random.uniform(1, 5) * 2) / 2  # Rating from 1 to 5, in 0.5 steps

                    session.run(
                        """
                        MATCH (u:User {id: $user_id})
                        MATCH (m:Movie {id: $movie_id})
                        MERGE (u)-[r:RATED]->(m)
                        SET r.rating = $rating
                        """,
                        user_id=user_id,
                        movie_id=movie_id,
                        rating=rating
                    )
                    print(f"User {user_id} rated movie {movie_id} with {rating}")

    driver.close()

# Function to get movie recommendations for a user
def get_movie_recommendations(user_id):
    """
    Get movie recommendations for a user based on:
    1. Movies they haven't seen
    2. Movies liked by users with similar tastes
    3. Movies in genres they like
    """
    driver = get_driver()

    recommendations = []

    with driver.session() as session:
        # Get movies the user hasn't rated,
        # but are highly rated by users with similar tastes
        result = session.run(
            """
            MATCH (target:User {id: $user_id})-[r1:RATED]->(m:Movie)
            MATCH (other:User)-[r2:RATED]->(m)
            WHERE other.id <> $user_id AND abs(r1.rating - r2.rating) < 1
            MATCH (other)-[r3:RATED]->(rec:Movie)
            WHERE r3.rating >= 4
            AND NOT EXISTS { MATCH (target)-[:RATED]->(rec) }
            WITH rec, count(*) AS strength, avg(r3.rating) AS avg_rating
            ORDER BY strength DESC, avg_rating DESC
            LIMIT 5
            RETURN rec
            """,
            user_id=user_id
        )

        for record in result:
            movie_data = dict(record["rec"].items())
            movie = Movie(**movie_data)
            recommendations.append(movie)

    driver.close()
    return recommendations

# Get movies directed by a specific director
def get_movies_by_director(director_name):
    """Get all movies directed by a specific director"""
    driver = get_driver()

    movies_list = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Director {name: $director_name})-[:DIRECTED]->(m:Movie)
            RETURN m
            """,
            director_name=director_name
        )

        for record in result:
            movie_data = dict(record["m"].items())
            movie = Movie(**movie_data)
            movies_list.append(movie)

    driver.close()
    return movies_list

# Get actors who worked with a specific actor
def get_co_actors(actor_name):
    """Get all actors who acted in the same movie as the specified actor"""
    driver = get_driver()

    co_actors = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Actor {name: $actor_name})-[:ACTED_IN]->(m:Movie)<-[:ACTED_IN]-(co:Actor)
            WHERE co.name <> $actor_name
            RETURN DISTINCT co
            """,
            actor_name=actor_name
        )

        for record in result:
            actor_data = dict(record["co"].items())
            actor = Actor(**actor_data)
            co_actors.append(actor)

    driver.close()
    return co_actors

# Main function to demo the movie recommendation system
def main():
    # Initialize and populate the database
    initialize_database()
    populate_database()

    # Get movie recommendations for User One
    print("\nMovie recommendations for User One:")
    recommendations = get_movie_recommendations("u1")
    for movie in recommendations:
        print(f"  - {movie.title} ({movie.year}) - Rating: {movie.rating}")

    # Get movies directed by Christopher Nolan
    print("\nMovies directed by Christopher Nolan:")
    nolan_movies = get_movies_by_director("Christopher Nolan")
    for movie in nolan_movies:
        print(f"  - {movie.title} ({movie.year}) - Rating: {movie.rating}")

    # Get actors who worked with Keanu Reeves
    print("\nActors who worked with Keanu Reeves:")
    keanu_co_actors = get_co_actors("Keanu Reeves")
    for actor in keanu_co_actors:
        print(f"  - {actor.name} (Age: {actor.age})")

if __name__ == "__main__":
    main()
```

## Error Handling with Neo4j Adapter

Let's demonstrate proper error handling for common Neo4j operations:

```python
from pydantic import BaseModel
from typing import List, Optional
from pydapter.extras.neo4j_ import Neo4jAdapter
from pydapter.exceptions import ConnectionError, QueryError, ResourceError, ValidationError

# Define a simple model
class Person(BaseModel):
    id: str
    name: str
    age: int

def neo4j_error_handling():
    print("Testing error handling for Neo4j operations...")

    # 1. Connection error - wrong authentication
    try:
        Neo4jAdapter.from_obj(
            Person,
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "wrong_password"),
                "label": "Person"
            }
        )
    except ConnectionError as e:
        print(f"Authentication error handled: {e}")

    # 2. Connection error - wrong host
    try:
        Neo4jAdapter.from_obj(
            Person,
            {
                "url": "bolt://nonexistent-host:7687",
                "auth": ("neo4j", "password"),
                "label": "Person"
            }
        )
    except ConnectionError as e:
        print(f"Host connection error handled: {e}")

    # 3. Query error - Cypher syntax error
    try:
        # Create a valid connection but inject a syntax error
        # Note: The adapter validates basic Cypher, but we can still get Neo4j errors
        Neo4jAdapter.from_obj(
            Person,
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "Person",
                "where": "n.age ==" # Invalid Cypher syntax (missing value)
            }
        )
    except QueryError as e:
        print(f"Cypher syntax error handled: {e}")

    # 4. Resource error - nonexistent label
    try:
        # This assumes the database is empty or this label doesn't exist
        Neo4jAdapter.from_obj(
            Person,
            {
                "url": "bolt://localhost:7687",
                "auth": ("neo4j", "password"),
                "label": "NonexistentLabel"
            }
        )
    except ResourceError as e:
        print(f"Resource error handled: {e}")

# Run the error handling examples
neo4j_error_handling()
```

## Using Neo4j with Adaptable Mixin

For a more ergonomic API, you can use the `Adaptable` mixin with the Neo4j
adapter:

```python
from pydantic import BaseModel
from typing import List, Optional
from pydapter.core import Adaptable
from pydapter.extras.neo4j_ import Neo4jAdapter

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# Define a model with the Adaptable mixin
class Product(BaseModel, Adaptable):
    id: str
    name: str
    price: float
    category: str
    in_stock: bool = True
    tags: List[str] = []

# Register the Neo4j adapter
Product.register_adapter(Neo4jAdapter)

def adaptable_mixin_demo():
    # Create products
    products = [
        Product(id="prod1", name="Laptop", price=1299.99, category="Electronics", tags=["computer", "portable"]),
        Product(id="prod2", name="Smartphone", price=899.99, category="Electronics", tags=["mobile", "portable"]),
        Product(id="prod3", name="Headphones", price=199.99, category="Audio", tags=["audio", "portable"])
    ]

    # Store products using the mixin
    print("Storing products using Adaptable mixin...")
    for product in products:
        result = product.adapt_to(
            obj_key="neo4j",
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Product",
            merge_on="id"
        )
        print(f"Stored {product.name}: {result}")

    # Retrieve products by category
    print("\nRetrieving electronics products...")
    electronics = Product.adapt_from(
        {
            "url": NEO4J_URI,
            "auth": NEO4J_AUTH,
            "label": "Product",
            "where": "n.category = 'Electronics'"
        },
        obj_key="neo4j",
        many=True
    )

    print(f"Found {len(electronics)} electronics products:")
    for product in electronics:
        print(f"  - {product.name}: ${product.price}")
        print(f"    Tags: {', '.join(product.tags)}")

# Run the adaptable mixin demo
adaptable_mixin_demo()
```

## Complete Example: Social Network Analysis

Let's build a more complete example that showcases Neo4j's strengths for social
network analysis:

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydapter.core import Adaptable
from pydapter.extras.neo4j_ import Neo4jAdapter
from neo4j import GraphDatabase
import random

# Neo4j connection settings
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")

# Define our models
class User(BaseModel, Adaptable):
    id: str
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    joined_date: Optional[str] = None

class Post(BaseModel, Adaptable):
    id: str
    content: str
    created_at: str
    likes: int = 0
    user_id: str  # Author of the post

# Register adapters
User.register_adapter(Neo4jAdapter)
Post.register_adapter(Neo4jAdapter)

# Helper function to create Neo4j driver
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# Initialize the database with schema and constraints
def initialize_database():
    driver = get_driver()

    with driver.session() as session:
        # Create constraints for uniqueness
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE")

    driver.close()
    print("Database initialized with constraints")

# Create relationships between users (follows) and between users and posts
def create_relationships(users, posts):
    driver = get_driver()

    with driver.session() as session:
        # Connect users with their posts
        print("\nConnecting users with their posts...")
        for post in posts:
            session.run(
                """
                MATCH (u:User {id: $user_id})
                MATCH (p:Post {id: $post_id})
                MERGE (u)-[:POSTED]->(p)
                """,
                user_id=post.user_id,
                post_id=post.id
            )
            print(f"Connected user {post.user_id} with post {post.id}")

        # Create random follow relationships between users
        print("\nCreating follow relationships...")
        user_ids = [user.id for user in users]

        for user_id in user_ids:
            # Each user follows a random subset of other users
            for other_id in user_ids:
                if user_id != other_id and random.random() < 0.3:  # 30% chance to follow
                    session.run(
                        """
                        MATCH (u1:User {id: $user_id})
                        MATCH (u2:User {id: $other_id})
                        MERGE (u1)-[:FOLLOWS]->(u2)
                        """,
                        user_id=user_id,
                        other_id=other_id
                    )
                    print(f"User {user_id} follows User {other_id}")

        # Create some likes on posts
        print("\nCreating likes on posts...")
        for user_id in user_ids:
            for post in posts:
                # Users don't like their own posts, and random chance to like others
                if post.user_id != user_id and random.random() < 0.4:  # 40% chance to like
                    session.run(
                        """
                        MATCH (u:User {id: $user_id})
                        MATCH (p:Post {id: $post_id})
                        MERGE (u)-[:LIKES]->(p)
                        """,
                        user_id=user_id,
                        post_id=post.id
                    )

                    # Also update the likes count on the post
                    session.run(
                        """
                        MATCH (p:Post {id: $post_id})
                        SET p.likes = p.likes + 1
                        """,
                        post_id=post.id
                    )

                    print(f"User {user_id} likes Post {post.id}")

    driver.close()

# Populate the database with users and posts
def populate_database():
    # Create some users
    users = [
        User(
            id="u1",
            username="alice_wonder",
            full_name="Alice Wonderland",
            email="alice@example.com",
            location="New York",
            joined_date=datetime(2022, 1, 15).isoformat()
        ),
        User(
            id="u2",
            username="bob_builder",
            full_name="Bob Builder",
            email="bob@example.com",
            location="San Francisco",
            joined_date=datetime(2022, 2, 20).isoformat()
        ),
        User(
            id="u3",
            username="charlie_brown",
            full_name="Charlie Brown",
            email="charlie@example.com",
            location="Chicago",
            joined_date=datetime(2022, 3, 10).isoformat()
        ),
        User(
            id="u4",
            username="david_jones",
            full_name="David Jones",
            email="david@example.com",
            location="Miami",
            joined_date=datetime(2022, 4, 5).isoformat()
        ),
        User(
            id="u5",
            username="emma_stone",
            full_name="Emma Stone",
            email="emma@example.com",
            location="Los Angeles",
            joined_date=datetime(2022, 5, 1).isoformat()
        ),
    ]

    # Create some posts
    posts = [
        Post(
            id="p1",
            content="Just learned about Neo4j and graph databases!",
            created_at=datetime(2023, 1, 5).isoformat(),
            user_id="u1"
        ),
        Post(
            id="p2",
            content="Excited to start my new project with Python",
            created_at=datetime(2023, 1, 10).isoformat(),
            user_id="u1"
        ),
        Post(
            id="p3",
            content="San Francisco has the best views!",
            created_at=datetime(2023, 1, 8).isoformat(),
            user_id="u2"
        ),
        Post(
            id="p4",
            content="Working on a new recommendation algorithm",
            created_at=datetime(2023, 1, 12).isoformat(),
            user_id="u3"
        ),
        Post(
            id="p5",
            content="Just finished reading a great book about AI",
            created_at=datetime(2023, 1, 15).isoformat(),
            user_id="u3"
        ),
        Post(
            id="p6",
            content="Miami sunsets are unbeatable!",
            created_at=datetime(2023, 1, 14).isoformat(),
            user_id="u4"
        ),
        Post(
            id="p7",
            content="Excited about new movie roles coming up",
            created_at=datetime(2023, 1, 18).isoformat(),
            user_id="u5"
        ),
    ]

    # Store users in Neo4j
    print("Storing users...")
    for user in users:
        user.adapt_to(
            obj_key="neo4j",
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="User",
            merge_on="id"
        )

    # Store posts in Neo4j
    print("\nStoring posts...")
    for post in posts:
        post.adapt_to(
            obj_key="neo4j",
            url=NEO4J_URI,
            auth=NEO4J_AUTH,
            label="Post",
            merge_on="id"
        )

    # Create relationships
    create_relationships(users, posts)

    print("Database populated with sample data")

# Function to get a user's feed (posts from users they follow)
def get_user_feed(user_id):
    """Get posts from users that this user follows"""
    driver = get_driver()

    feed_posts = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})-[:FOLLOWS]->(friend:User)-[:POSTED]->(p:Post)
            RETURN p, friend.username AS author
            ORDER BY p.created_at DESC
            LIMIT 10
            """,
            user_id=user_id
        )

        for record in result:
            post_data = dict(record["p"].items())
            post = Post(**post_data)
            author = record["author"]
            feed_posts.append((post, author))

    driver.close()
    return feed_posts

# Function to get recommended users to follow
def get_follow_recommendations(user_id):
    """Recommend users to follow based on mutual connections"""
    driver = get_driver()

    recommended_users = []

    with driver.session() as session:
        # Find users who are followed by people the user follows,
        # but the user doesn't follow yet
        result = session.run(
            """
            MATCH (user:User {id: $user_id})-[:FOLLOWS]->(mutual:User)-[:FOLLOWS]->(recommended:User)
            WHERE NOT (user)-[:FOLLOWS]->(recommended)
            AND user.id <> recommended.id
            WITH recommended, count(mutual) AS mutualCount
            ORDER BY mutualCount DESC
            LIMIT 5
            RETURN recommended
            """,
            user_id=user_id
        )

        for record in result:
            user_data = dict(record["recommended"].items())
            user = User(**user_data)
            recommended_users.append(user)

    driver.close()
    return recommended_users

# Function to get popular posts
def get_popular_posts():
    """Get posts with the most likes"""
    driver = get_driver()

    popular_posts = []

    with driver.session() as session:
        result = session.run(
            """
            MATCH (p:Post)
            WITH p, p.likes AS likes
            ORDER BY likes DESC
            LIMIT 5
            MATCH (author:User)-[:POSTED]->(p)
            RETURN p, author.username AS author
            """
        )

        for record in result:
            post_data = dict(record["p"].items())
            post = Post(**post_data)
            author = record["author"]
            popular_posts.append((post, author))

    driver.close()
    return popular_posts

# Main function to demo the social network
def main():
    # Initialize and populate the database
    initialize_database()
    populate_database()

    # Get user feed for Alice
    print("\nAlice's feed (posts from people she follows):")
    feed = get_user_feed("u1")
    for post, author in feed:
        print(f"@{author}: {post.content}")
        print(f"  Likes: {post.likes} | Posted: {post.created_at}")

    # Get recommended users for Bob to follow
    print("\nRecommended users for Bob to follow:")
    recommendations = get_follow_recommendations("u2")
    for user in recommendations:
        print(f"  - {user.full_name} (@{user.username}) from {user.location}")

    # Get popular posts
    print("\nPopular posts across the network:")
    popular = get_popular_posts()
    for i, (post, author) in enumerate(popular):
        print(f"{i+1}. @{author}: {post.content}")
        print(f"   Likes: {post.likes}")

if __name__ == "__main__":
    main()
```

## Conclusion

In this tutorial, you've learned how to use pydapter's Neo4j adapter to
seamlessly work with graph databases. We've covered:

1. Basic setup and connection to Neo4j
2. Modeling entities as Pydantic models
3. Storing and retrieving data using the Neo4j adapter
4. Creating and traversing relationships
5. Building more complex graph applications
6. Error handling and best practices

Neo4j's graph structure is particularly powerful for data with complex
relationships, like social networks, recommendation systems, and knowledge
graphs. The pydapter adapter makes it easy to integrate Neo4j with your
Pydantic-based Python applications, providing a clean interface for graph
database operations.

Some key advantages of using pydapter's Neo4j adapter include:

1. Type safety and validation through Pydantic models
2. Consistent error handling
3. Simplified node creation and retrieval
4. Integration with other pydapter adapters for multi-database applications

Keep in mind that while the adapter handles nodes well, for relationship
operations you'll often need to use the Neo4j driver directly for more complex
graph traversals and Cypher queries.

To learn more about Neo4j and graph modeling, check out the
[Neo4j documentation](https://neo4j.com/docs/) and
[Cypher query language](https://neo4j.com/developer/cypher/).
