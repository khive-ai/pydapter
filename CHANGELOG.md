# Changelog

## 0.1.5 - 2025-05-14

### Added

- New adapter implementations:
  - `AsyncNeo4jAdapter` - Asynchronous adapter for Neo4j graph database with
    comprehensive error handling
  - `WeaviateAdapter` - Synchronous adapter for Weaviate vector database with
    vector search capabilities
  - `AsyncWeaviateAdapter` - Asynchronous adapter for Weaviate vector database
    using aiohttp for REST API calls

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
