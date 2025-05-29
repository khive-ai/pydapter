# Changelog

## 0.2.3 - 2025-05-29

### Added

- **Field Families and Common Patterns Library** (Issue #114): Introduced a
  comprehensive field system with:
  - `FieldTemplate`: Reusable field definitions with flexible naming
  - `FieldFamilies`: Core database pattern collections (ENTITY, SOFT_DELETE, AUDIT)
  - `DomainModelBuilder`: Fluent API for building models with method chaining
  - `ProtocolFieldFamilies`: Field sets that ensure protocol compliance
  - `ValidationPatterns`: Common regex patterns and constraint builders
  - `create_protocol_model()`: Function to create protocol-compliant models (structure only)
- **Protocol Enhancements**:
  - Added protocol constants (`IDENTIFIABLE`, `TEMPORAL`, etc.) for type-safe protocol selection
  - Added `create_protocol_model_class()`: Factory function that creates models with both
    structural fields AND behavioral methods in one step
  - Added `combine_with_mixins()`: Helper to easily add protocol behaviors to existing models

### Changed

- **BREAKING**: Removed "event" from the protocol system in `ProtocolFieldFamilies`.
  The `Event` class remains available but is no longer part of the protocol
  selection system since it's a concrete class, not a protocol interface.

### Fixed

- Fixed import organization issues (E402 errors)
- Updated tests to reflect simplified field families
- Fixed email validation test expectations
- Updated documentation to align with new architecture
- Fixed SQLAlchemy primary key mapping issue in test_model_adapter_enhancements.py

## 0.2.0 - 2025-05-24

### Highlights

This release introduces two major foundational modules: **Fields** and
**Protocols**. These modules provide a robust and extensible framework for
defining data structures and behaviors within `pydapter`.

- **Fields Module (`pydapter.fields`)**: A powerful system for defining typed,
  validated, and serializable fields. It includes pre-defined field types for
  common use cases like IDs, datetimes, embeddings, and execution tracking,
  along with a flexible `Field` class for custom definitions and a
  `create_model` utility for dynamic Pydantic model creation.
- **Protocols Module (`pydapter.protocols`)**: A set of composable interfaces
  (e.g., `Identifiable`, `Temporal`, `Embeddable`, `Invokable`,
  `Cryptographical`) that define standard behaviors for Pydantic models. The
  `Event` protocol combines these to offer comprehensive event tracking
  capabilities, enhanced by the `@as_event` decorator for easily instrumenting
  functions.

These additions significantly enhance `pydapter`'s ability to model complex data
interactions and workflows in a standardized and maintainable way.

### Added

- **New `pydapter.fields` module**: Introduced a robust system for defining
  typed, validated, and serializable fields (e.g., IDs, datetimes, embeddings,
  execution tracking) and a `create_model` utility for dynamic Pydantic model
  creation. (Related to Issue #100, PR #99)
- **New `pydapter.protocols` module**: Added composable protocol interfaces
  (`Identifiable`, `Temporal`, `Embeddable`, `Invokable`, `Cryptographical`) and
  an `Event` protocol with an `@as_event` decorator for comprehensive event
  modeling and function instrumentation. (Related to Issue #100, PR #99)
- **Hybrid Documentation System**: Implemented a new documentation system
  combining auto-generated API skeletons with rich manual content and automated
  validation (markdown linting, link checking). (Issue #103, PR #104)
- Updated CI to install documentation validation tools. (Issue #105)

### Fixed

- Resolved Python 3.10 compatibility issues related to `datetime.timezone.utc`.
  (Part of PR #99 fixes)
- Addressed various `mkdocs` build warnings and broken links in the
  documentation. (Part of PR #104 fixes)

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
