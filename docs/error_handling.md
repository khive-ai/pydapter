# Error Handling in pydapter

pydapter provides a comprehensive error handling system to help you diagnose and
resolve issues when working with adapters. This document explains the exception
hierarchy and how to handle errors effectively in your applications.

## Exception Hierarchy

All pydapter exceptions inherit from the base `AdapterError` class, which
provides context-rich error messages and a consistent interface for error
handling.

```
AdapterError
├── ValidationError
├── ParseError
├── ConnectionError
├── QueryError
├── ResourceError
├── ConfigurationError
└── AdapterNotFoundError
```

### AdapterError

The base exception class for all pydapter errors. It provides a mechanism to
attach context information to errors.

```python
try:
    # Some adapter operation
except AdapterError as e:
    print(f"Error message: {e.message}")
    print(f"Error context: {e.context}")
```

### ValidationError

Raised when data validation fails, such as when required fields are missing or
have incorrect types.

```python
try:
    model = MyModel.adapt_from(invalid_data, obj_key="json")
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Invalid data: {e.data}")
```

### ParseError

Raised when data parsing fails, such as when trying to parse invalid JSON, CSV,
or TOML.

```python
try:
    model = MyModel.adapt_from('{"invalid": json', obj_key="json")
except ParseError as e:
    print(f"Parse error: {e}")
    print(f"Source: {e.source}")
```

### ConnectionError

Raised when a connection to a data source fails, such as when a database is
unavailable.

```python
try:
    model = MyModel.adapt_from({"engine_url": "invalid://url", "table": "test"}, obj_key="sql")
except ConnectionError as e:
    print(f"Connection failed: {e}")
    print(f"Adapter: {e.adapter}")
    print(f"URL: {e.url}")
```

### QueryError

Raised when a query to a data source fails, such as when an SQL query contains
errors.

```python
try:
    model = MyModel.adapt_from({"engine_url": "sqlite://", "table": "test", "query": "INVALID SQL"}, obj_key="sql")
except QueryError as e:
    print(f"Query failed: {e}")
    print(f"Query: {e.query}")
    print(f"Adapter: {e.adapter}")
```

### ResourceError

Raised when a resource (file, database table, etc.) cannot be accessed.

```python
try:
    model = MyModel.adapt_from(Path("nonexistent.json"), obj_key="json")
except ResourceError as e:
    print(f"Resource error: {e}")
    print(f"Resource: {e.resource}")
```

### ConfigurationError

Raised when adapter configuration is invalid, such as when required parameters
are missing.

```python
try:
    model = MyModel.adapt_from({"missing": "required_params"}, obj_key="sql")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print(f"Config: {e.config}")
```

### AdapterNotFoundError

Raised when an adapter is not found for a given `obj_key`.

```python
try:
    model = MyModel.adapt_from({}, obj_key="nonexistent")
except AdapterNotFoundError as e:
    print(f"Adapter not found: {e}")
    print(f"Object key: {e.obj_key}")
```

## Error Handling Best Practices

### Catch Specific Exceptions

Catch the most specific exception type that applies to your situation:

```python
try:
    model = MyModel.adapt_from(data, obj_key="json")
except ParseError:
    # Handle parsing errors
except ValidationError:
    # Handle validation errors
except AdapterError:
    # Handle any other adapter errors
```

### Provide Context in Error Messages

When raising custom exceptions, provide as much context as possible:

```python
raise ConnectionError(
    "Failed to connect to database",
    adapter="postgres",
    url="postgresql://localhost:5432/mydb",
    timeout=30
)
```

### Handle Asynchronous Errors

For asynchronous adapters, use try/except blocks within async functions:

```python
async def fetch_data():
    try:
        return await MyModel.adapt_from_async(data, obj_key="async_mongo")
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        # Handle connection error
    except AdapterError as e:
        logger.error(f"Adapter error: {e}")
        # Handle other adapter errors
```

### Resource Cleanup

Ensure resources are properly cleaned up, even in error scenarios:

```python
try:
    # Some operation that acquires resources
    result = perform_operation()
    return result
except AdapterError:
    # Handle the error
    raise
finally:
    # Clean up resources
    cleanup_resources()
```

## Common Error Scenarios and Solutions

### JSON Parsing Errors

```python
try:
    model = MyModel.adapt_from(json_data, obj_key="json")
except ParseError as e:
    if "Expecting property name" in str(e):
        # Handle malformed JSON
    elif "Expecting value" in str(e):
        # Handle empty JSON
```

### Database Connection Errors

```python
try:
    model = MyModel.adapt_from(db_config, obj_key="postgres")
except ConnectionError as e:
    if "authentication failed" in str(e):
        # Handle authentication issues
    elif "connection refused" in str(e):
        # Handle server unavailable
    elif "database does not exist" in str(e):
        # Handle missing database
```

### Empty Result Sets

```python
try:
    model = MyModel.adapt_from(query_params, obj_key="mongo", many=False)
except ResourceError as e:
    if "No documents found" in str(e):
        # Handle empty result
        return default_value
```

## Conclusion

Proper error handling is essential for building robust applications with
pydapter. By understanding the exception hierarchy and following best practices,
you can create more resilient code that gracefully handles failure scenarios and
provides clear feedback to users.
