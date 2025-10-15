# Release Notes - Pydapter v1.2.0

**Release Date**: 2025-10-14

## Overview

Version 1.2.0 represents a significant evolution of Pydapter with a **framework-agnostic architecture**, **comprehensive error handling overhaul**, and **major improvements to adapter reliability and test coverage**.

---

## 🎯 Major Changes

### Framework-Agnostic Architecture

Pydapter now supports **all Python objects**, not just Pydantic models:

- ✅ Works with dataclasses, TypedDict, plain classes, and any Python object
- ✅ Pydantic remains a dependency for backward compatibility
- ✅ Existing Pydantic-based code continues to work without changes

**Migration**: No action required - all existing code remains compatible.

---

### Complete Error Handling Overhaul

Standardized exception hierarchy across all adapters:

```python
# New exception structure
pydapter.exceptions.
├── AdapterError (base)
├── ValidationError (input validation)
├── ConnectionError (network/connection issues)
├── QueryError (operation failures)
└── ResourceError (missing resources)
```

**Benefits**:
- Consistent error handling patterns across all adapters
- Better error messages with context and troubleshooting hints
- Easier debugging with detailed exception information

---

### Adapter Refactoring

All adapters refactored to align with new error handling standards:

- **PostgreSQL**: Enhanced type support, better connection error handling
- **MongoDB**: Comprehensive async error handling, 40+ new tests
- **Weaviate**: Fixed critical vector retrieval bug, improved async support
- **Qdrant**: Resource management fixes, better validation
- **Neo4j**: Improved async context handling

---

## 🐛 Critical Bug Fixes

### 1. WeaviateAdapter Vector Field Missing (CRITICAL)

**Issue**: `WeaviateAdapter.from_obj()` returned results without vector embeddings

**Impact**: Searches returned incomplete data, breaking downstream vector operations

**Fix**: Updated `.with_additional()` to request `["id", "vector"]` instead of just `"id"`

```python
# BEFORE (BUGGY)
.with_additional("id")  # Missing vector!

# AFTER (FIXED)
.with_additional(["id", "vector"])  # Includes vector in response
```

**Files**: `src/pydapter/extras/weaviate_.py:314`

---

### 2. AsyncWeaviateAdapter Test Failures

**Issue**: 20 out of 29 async tests failing due to improper async context manager mocking

**Impact**: Unreliable async operations, hard-to-debug test failures

**Fix**: Corrected async mocking pattern for `aiohttp.ClientSession`

```python
# Correct pattern
mock_session = mocker.MagicMock()
mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
mock_session.__aexit__ = mocker.AsyncMock(return_value=None)
```

**Coverage**: async_weaviate_ 37% → 78% (all 29 tests passing)

---

### 3. PostgresModelAdapter IPv4/IPv6 Type Support

**Issue**: `TypeConversionError` for `ipaddress` types when using classmethods

**Impact**: Network-related models failed with cryptic errors

**Fix**: Added module-level type registration for all IPv4/IPv6 types

**Types Added**:
- `IPv4Address`, `IPv6Address`
- `IPv4Interface`, `IPv6Interface`
- `IPv4Network`, `IPv6Network`

**Files**: `src/pydapter/model_adapters/postgres_model.py`

---

### 4. Pydantic v2 Migration

**Issue**: 12 deprecation warnings from Pydantic v1 `class Config:` pattern

**Fix**: Migrated to Pydantic v2 `model_config = ConfigDict(...)`

```python
# BEFORE (Deprecated)
class Config:
    arbitrary_types_allowed = True

# AFTER (Pydantic v2)
model_config = ConfigDict(arbitrary_types_allowed=True)
```

**Impact**: Zero deprecation warnings, future-proof for Pydantic v3

---

### 5. pytest_asyncio Compatibility

**Issue**: 15 warnings about using `@pytest.fixture` for async fixtures

**Fix**: Changed to `@pytest_asyncio.fixture` for all async test fixtures

**Impact**: Clean test runs with no warnings

---

## 📊 Test Coverage Improvements

### Before → After

| Adapter | Before | After | Change |
|---------|--------|-------|--------|
| **async_mongo_** | 76% | **95%** | +19% |
| **async_weaviate_** | 37% | **78%** | +41% |
| **weaviate_** | 67% | **79%** | +12% |
| **Overall Project** | 79% | **83%** | +4% |

### New Tests Added

- **async_mongo_**: 40+ comprehensive tests covering error paths
- **async_weaviate_**: Complete async context manager testing
- **weaviate_**: Enhanced vector field validation tests

---

## 🔧 Technical Improvements

### Error Handling Patterns

All adapters now follow consistent patterns:

```python
try:
    # Adapter operation
except SpecificError as e:
    raise AdapterError(
        "User-friendly message",
        details={"context": "debugging info"},
        adapter="adapter_name"
    ) from e
```

### Resource Management

Improved async resource cleanup:

```python
async def operation():
    client = await _client(url)
    try:
        # Operations
    finally:
        await client.close()  # Always cleanup
```

---

## 📦 What's Included

### Source Changes

- `src/pydapter/core.py` - Framework-agnostic adapter protocol
- `src/pydapter/extras/weaviate_.py` - Vector field bug fix
- `src/pydapter/extras/async_weaviate_.py` - Async improvements
- `src/pydapter/model_adapters/postgres_model.py` - IPv4/IPv6 support
- All test files migrated to Pydantic v2 patterns

### Test Improvements

- 40+ new async_mongo_ tests
- Enhanced async_weaviate_ test coverage
- Comprehensive error handling tests
- Integration test improvements

---

## 🚀 Upgrade Guide

### For Existing Users

**No breaking changes** - v1.2.0 is fully backward compatible.

```bash
# Upgrade via pip
pip install --upgrade pydapter

# Upgrade via uv
uv pip install --upgrade pydapter
```

### Recommended Actions

1. **Review error handling** - Update exception catches to use new exception types
2. **Test async operations** - Verify async adapters work correctly
3. **Check network types** - If using PostgreSQL with IPv4/IPv6, test thoroughly

---

## 🔍 Known Issues

None identified in this release.

---

## 📝 Contributors

This release includes contributions from the Pydapter team focusing on:
- Error handling standardization
- Test coverage improvements
- Bug fixes and reliability enhancements

---

## 🔗 Resources

- **Documentation**: https://github.com/khive-ai/pydapter
- **Issues**: https://github.com/khive-ai/pydapter/issues
- **Pull Request**: #143

---

## Next Steps

Looking ahead to v1.3.0:
- Further coverage improvements for remaining adapters
- Performance optimizations for batch operations
- Additional database adapter support

---

**Full Changelog**: See [CHANGELOG.md](CHANGELOG.md) for complete details.
