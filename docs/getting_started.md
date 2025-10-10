# Getting Started with Pydapter

Pydapter is a powerful adapter library that lets you easily convert between
Pydantic models and various data formats. With the new field system (v0.3.0),
creating robust models is easier than ever!

## Installation

First, let's install pydapter and its dependencies:

```bash
# Create a virtual environment (optional but recommended)
python -m venv pydapter-demo
source pydapter-demo/bin/activate  # On Windows: pydapter-demo\Scripts\activate

# Install pydapter and dependencies
uv pip install pydapter
uv pip install pandas  # For DataFrameAdapter and SeriesAdapter
uv pip install xlsxwriter  # For ExcelAdapter
uv pip install openpyxl  # Also needed for Excel support

# Install optional modules
uv pip install "pydapter[protocols]"      # For standardized model interfaces
uv pip install "pydapter[migrations-sql]" # For database schema migrations

# or install all adapters at once
uv pip install "pydapter[all]"
```

## Creating Models with the Field System

### Option 1: Using Field Families (New!)

```python
from pydapter.fields import DomainModelBuilder, FieldTemplate
from pydapter.protocols import (
    create_protocol_model_class,
    IDENTIFIABLE,
    TEMPORAL
)

# Build a model with field families
User = (
    DomainModelBuilder("User")
    .with_entity_fields()  # Adds id, created_at, updated_at
    .add_field("name", FieldTemplate(base_type=str))
    .add_field("email", FieldTemplate(base_type=str))
    .add_field("active", FieldTemplate(base_type=bool, default=True))
    .add_field("tags", FieldTemplate(base_type=list[str], default_factory=list))
    .build()
)

# Or create a protocol-compliant model with behaviors
User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,  # Adds id field
    TEMPORAL,      # Adds created_at, updated_at + update_timestamp() method
    name=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str),
    active=FieldTemplate(base_type=bool, default=True),
    tags=FieldTemplate(base_type=list[str], default_factory=list)
)
```

### Option 2: Traditional Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List
from pydapter.adapters.json_ import JsonAdapter

# Define a traditional Pydantic model
class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True
    tags: List[str] = []

```

## Using Adapters

Once you have your models, you can use pydapter's adapters to convert data:

```python
from pydapter.adapters.json_ import JsonAdapter

# Create some test data
users = [
    User(id=1, name="Alice", email="alice@example.com", tags=["admin", "staff"]),
    User(id=2, name="Bob", email="bob@example.com", active=False),
    User(id=3, name="Charlie", email="charlie@example.com", tags=["staff"]),
]

# If using protocol models with behaviors
if hasattr(users[0], 'update_timestamp'):
    users[0].update_timestamp()  # Updates the updated_at field

# Convert models to JSON
json_data = JsonAdapter.to_obj(users, many=True)
print("JSON Output:")
print(json_data)

# Convert JSON back to models
loaded_users = JsonAdapter.from_obj(User, json_data, many=True)
print("\nLoaded users:")
for user in loaded_users:
    print(f"{user.name} ({user.email}): Active={user.active}, Tags={user.tags}")
```

## Using the Adaptable Mixin for Better Ergonomics

Pydapter provides an `Adaptable` mixin that makes the API more ergonomic:

```python
from pydantic import BaseModel
from typing import List
from pydapter.core import Adaptable
from pydapter.adapters.json_ import JsonAdapter

# Define a model with the Adaptable mixin
class Product(BaseModel, Adaptable):
    id: int
    name: str
    price: float
    in_stock: bool = True

# Register the JSON adapter
Product.register_adapter(JsonAdapter)

# Create a product
product = Product(id=101, name="Laptop", price=999.99)

# Convert to JSON using the mixin method
json_data = product.adapt_to(obj_key="json")
print("JSON Output:")
print(json_data)

# Convert back to a model
loaded_product = Product.adapt_from(json_data, obj_key="json")
print(f"\nLoaded product: {loaded_product.name} (${loaded_product.price})")
```

## Working with CSV

Here's how to use the CSV adapter:

```python
from pydantic import BaseModel
from pydapter.adapters.csv_ import CsvAdapter

# Define a Pydantic model
class Employee(Adaptable, BaseModel):
    id: int
    name: str
    department: str
    salary: float
    hire_date: str

# Create some sample data
employees = [
    Employee(
        id=1, name="Alice", department="Engineering",
        salary=85000, hire_date="2020-01-15"
    ),
    Employee(
        id=2, name="Bob", department="Marketing",
        salary=75000, hire_date="2021-03-20"
    ),
    Employee(
        id=3, name="Charlie", department="Finance",
        salary=95000, hire_date="2019-11-01"
    ),
]

csv_data = CsvAdapter.to_obj(employees, many=True)
print("CSV Output:")
print(csv_data)

# Convert CSV back to models
loaded_employees = CsvAdapter.from_obj(Employee, csv_data, many=True)
print("\nLoaded employees:")
for employee in loaded_employees:
    print(f"{employee.name} - {employee.department} (${employee.salary})")

# You can also save to a file and read from a file
from pathlib import Path

# Save to file
Path("employees.csv").write_text(csv_data)

# Read from file
file_employees = CsvAdapter.from_obj(Employee, Path("employees.csv"), many=True)
```

## Working with TOML

Here's how to use the TOML adapter:

```python
from pydantic import BaseModel
from typing import List, Dict, Optional
from pydapter.adapters.toml_ import TomlAdapter

# Define a Pydantic model

class AppConfig(BaseModel):
    app_name: str
    version: str
    debug: bool = False
    database: Dict[str, str] = {}
    allowed_hosts: List[str] = []

# Create a config

config = AppConfig(
    app_name="MyApp",
    version="1.0.0",
    debug=True,
    database={"host": "localhost", "port": "5432", "name": "myapp"},
    allowed_hosts=["localhost", "example.com"]
)

# Convert to TOML
toml_data = TomlAdapter.to_obj(config)
print("TOML Output:")
print(toml_data)

# Convert TOML back to model
loaded_config = TomlAdapter.from_obj(AppConfig, toml_data)
print("\nLoaded config:")
print(f"App: {loaded_config.app_name} v{loaded_config.version}")
print(f"Debug mode: {loaded_config.debug}")
print(f"Database: {loaded_config.database}")
print(f"Allowed hosts: {loaded_config.allowed_hosts}")

# Save to file
Path("config.toml").write_text(toml_data)

# Read from file
file_config = TomlAdapter.from_obj(AppConfig, Path("config.toml"))
```

## Working with Pandas DataFrame

Here's how to use the DataFrame adapter:

```python
import pandas as pd
from pydantic import BaseModel
from pydapter.extras.pandas_ import DataFrameAdapter

# Define a Pydantic model
class SalesRecord(BaseModel):
    id: int
    product: str
    quantity: int
    price: float
    date: str

# Create a sample DataFrame

df = pd.DataFrame([
    {
        "id": 1, "product": "Laptop", "quantity": 2,
        "price": 999.99, "date": "2023-01-15"
    },
    {
        "id": 2, "product": "Monitor", "quantity": 3,
        "price": 249.99, "date": "2023-01-20"
    },
    {
        "id": 3, "product": "Mouse", "quantity": 5,
        "price": 29.99, "date": "2023-01-25"
    }
])

# Convert DataFrame to models
sales_records = DataFrameAdapter.from_obj(SalesRecord, df, many=True)
print("DataFrame to Models:")
for record in sales_records:
    print(f"{record.id}: {record.quantity} x {record.product} at ${record.price}")

# Convert models back to DataFrame
new_df = DataFrameAdapter.to_obj(sales_records, many=True)
print("\nModels to DataFrame:")
print(new_df)
```

## Working with Excel Files

Here's how to use the Excel adapter:

```python
from pydantic import BaseModel
from typing import List, Optional
from pydapter.extras.excel_ import ExcelAdapter
from pathlib import Path

# Define a Pydantic model
class Student(BaseModel):
    id: int
    name: str
    grade: str
    score: float

# Create some sample data

students = [
    Student(id=1, name="Alice", grade="A", score=92.5),
    Student(id=2, name="Bob", grade="B", score=85.0),
    Student(id=3, name="Charlie", grade="A-", score=90.0),
]

# Convert to Excel and save to file

excel_data = ExcelAdapter.to_obj(students, many=True, sheet_name="Students")
with open("students.xlsx", "wb") as f:
    f.write(excel_data)

print("Excel file saved as 'students.xlsx'")

# Read from Excel file

loaded_students = ExcelAdapter.from_obj(
    Student, Path("students.xlsx"), many=True
)
print("\nLoaded students:")
for student in loaded_students:
    print(f"{student.name}: {student.grade} ({student.score})")
```

## Error Handling

Let's demonstrate proper error handling:

```python
from pydantic import BaseModel, Field
from pydapter.adapters.json_ import JsonAdapter
from pydapter.exceptions import ParseError, ValidationError as AdapterValidationError

# Define a model with validation constraints
class Product(BaseModel):
    id: int = Field(gt=0)  # Must be greater than 0
    name: str = Field(min_length=3)  # Must be at least 3 characters
    price: float = Field(gt=0.0)  # Must be greater than 0

# Handle parsing errors

try:
    # Try to parse invalid JSON
    invalid_json = "{ 'id': 1, 'name': 'Laptop', price: 999.99 }"  # Note the
                                                                   # missing
                                                                   # quotes
                                                                   # around
                                                                   # 'price'
    product = JsonAdapter.from_obj(Product, invalid_json)
except ParseError as e:
    print(f"Parsing error: {e}")

# Handle validation errors

try:
    # Try to create a model with invalid data
    valid_json = '{"id": 0, "name": "A", "price": -10.0}'  # All fields
                                                           # violate
                                                           # constraints
    product = JsonAdapter.from_obj(Product, valid_json)
except AdapterValidationError as e:
    print(f"Validation error: {e}")
    if hasattr(e, 'errors') and callable(e.errors):
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")
```

## Using Protocols

Pydapter provides a set of standardized interfaces through the protocols module.
These protocols allow you to add common capabilities to your models:

```python
from pydapter.protocols import Identifiable, Temporal

# Define a model with standardized interfaces

class User(Identifiable, Temporal):
    name: str
    email: str

# Create a user

user = User(name="Alice", email="alice@example.com")

# Access standardized properties
print(f"User ID: {user.id}")  # Automatically generated UUID
print(f"Created at: {user.created_at}")  # Automatically set timestamp

# Update the timestamp

user.name = "Alicia"
user.update_timestamp()
print(f"Updated at: {user.updated_at}")
```

For more details, see the [Protocols documentation](protocols.md) and the
[Using Protocols tutorial](tutorials/using_protocols.md).

## Using Migrations

Pydapter provides tools for managing database schema changes through the
migrations module:

```python
from pydapter.migrations import AlembicAdapter
import mymodels  # Module containing your SQLAlchemy models

# Initialize migrations

AlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb",
    models_module=mymodels
)

# Create a migration

revision = AlembicAdapter.create_migration(
    message="Create users table",
    autogenerate=True,
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)

# Apply migrations

AlembicAdapter.upgrade(
    revision="head",
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
```

For more details, see the [Migrations documentation](migrations.md) and the
[Using Migrations tutorial](tutorials/using_migrations.md).
