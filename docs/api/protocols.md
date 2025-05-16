# Protocols API Reference

This page provides detailed API documentation for the `pydapter.protocols`
module.

## Installation

The protocols module is available as an optional dependency:

```bash
pip install "pydapter[protocols]"
```

## Module Overview

The protocols module provides standardized interfaces for models, following a
hierarchical structure:

```
Identifiable
    │
    ├── Temporal
    │       │
    │       ├── Embedable
    │       │
    │       └── Invokable
    │               │
    │               └── Event
    │
    └── Other custom protocols...
```

## Core Protocols

### Identifiable

::: pydapter.protocols.identifiable.Identifiable options: show_root_heading:
true show_source: true

### Temporal

::: pydapter.protocols.temporal.Temporal options: show_root_heading: true
show_source: true

### Embedable

::: pydapter.protocols.embedable.Embedable options: show_root_heading: true
show_source: true

### Invokable

::: pydapter.protocols.invokable.Invokable options: show_root_heading: true
show_source: true

### Event

::: pydapter.protocols.event.Event options: show_root_heading: true show_source:
true

::: pydapter.protocols.event.EventHandler options: show_root_heading: true
show_source: true

## Types

::: pydapter.protocols.types.Embedding options: show_root_heading: true
show_source: true

::: pydapter.protocols.types.ExecutionStatus options: show_root_heading: true
show_source: true

::: pydapter.protocols.types.Execution options: show_root_heading: true
show_source: true

::: pydapter.protocols.types.Log options: show_root_heading: true show_source:
true

## Utility Functions

::: pydapter.protocols.utils options: show_root_heading: true show_source: true
