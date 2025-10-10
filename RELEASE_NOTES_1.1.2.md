# Pydapter 1.1.2 Release Notes

## 🎯 Main Features

### AsyncRedisAdapter Enhancements
- **Comprehensive Redis Support**: Full async Redis adapter with msgpack and JSON serialization
- **Advanced Features**: TTL support, conditional operations (NX/XX), pattern-based retrieval
- **Production Ready**: Extensive test coverage with testcontainers for reliability

## 🐛 Bug Fixes & Improvements

### Python 3.10 Compatibility
- Fixed `NotRequired`, `Required`, `TypedDict` imports for Python 3.10
- Fixed `isinstance()` syntax for Python 3.10 compatibility
- Ensured full cross-version support (Python 3.10+)

### AsyncNeo4jAdapter Fixes
- Fixed async context manager behavior
- Improved query result processing
- Better error handling for async operations

### Developer Experience
- Improved CI/CD pipeline with better error reporting
- Enhanced test isolation (unit tests no longer require Docker)
- Auto-fixed 97+ linting issues for cleaner codebase
- Dynamic coverage thresholds based on test suite scope

## 📦 Installation

```bash
pip install pydapter==1.1.2

# With Redis support
pip install pydapter[redis]==1.1.2
```

## 🔗 Links

- [Full Changelog](https://github.com/khive-ai/pydapter/compare/v1.1.1...v1.1.2)
- [Documentation](https://github.com/khive-ai/pydapter)
- [Redis Adapter Guide](docs/crud_operations.md)
