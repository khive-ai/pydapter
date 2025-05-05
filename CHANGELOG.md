# Changelog

## 0.1.1 - 2025-05-04

### Added

- Integration tests for database adapters using TestContainers
  - PostgreSQL integration tests
  - MongoDB integration tests
  - Neo4j integration tests
  - Qdrant vector database integration tests

### Fixed

- Neo4j adapter now supports authentication
- Qdrant adapter improved connection error handling
- SQL adapter enhanced error handling for connection issues
- Improved error handling in core adapter classes

## 0.1.0 - 2025-05-03

- Initial public release.
  - `core.Adapter`, `AdapterRegistry`, `Adaptable`
  - Built-in JSON adapter
