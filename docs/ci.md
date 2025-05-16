# Continuous Integration

This document describes the continuous integration (CI) setup for the pydapter
project and how to use it locally.

## Overview

The pydapter project uses a comprehensive CI system that runs:

- Linting checks (using ruff)
- Code formatting checks (using ruff format)
- Type checking (using mypy)
- Unit tests (using pytest)
- Integration tests (using pytest)
- Coverage reporting

The CI system is implemented as a Python script that can be run both locally and
in GitHub Actions workflows, ensuring consistency between local development and
CI environments.

## Prerequisites

Before running the CI script, you need to ensure all dependencies are installed.
The easiest way to do this is to use the `uv sync` command with the
`--extra all` option:

```bash
# Install all dependencies including those needed for testing
uv sync --extra all
```

This will install all the dependencies defined in the `pyproject.toml` file,
including those needed for testing and integration with external services.

## Running CI Locally

The CI script is located at `scripts/ci.py` and can be run with various options
to customize the checks performed.

### Basic Usage

To run all CI checks:

```bash
python scripts/ci.py
```

This will run all linting, type checking, unit tests, integration tests, and
coverage reporting.

### Running Specific Components

You can run only specific components using the `--only` option:

```bash
# Run only linting checks
python scripts/ci.py --only lint

# Run only type checking
python scripts/ci.py --only type

# Run only unit tests
python scripts/ci.py --only unit

# Run only integration tests
python scripts/ci.py --only integration

# Run only coverage report
python scripts/ci.py --only coverage
```

### Skipping Specific Checks

You can skip specific checks using the following options:

```bash
# Skip linting checks
python scripts/ci.py --skip-lint

# Skip type checking
python scripts/ci.py --skip-type-check

# Skip unit tests
python scripts/ci.py --skip-unit

# Skip integration tests
python scripts/ci.py --skip-integration

# Skip coverage reporting
python scripts/ci.py --skip-coverage
```

You can combine these options to run only the checks you're interested in:

```bash
# Run only unit tests
python scripts/ci.py --skip-lint --skip-type-check --skip-integration --skip-coverage
```

### Handling External Dependencies

Some tests require external dependencies like databases (MongoDB, Neo4j, Qdrant,
etc.). You can skip these tests using the `--skip-external-deps` option:

```bash
python scripts/ci.py --skip-external-deps
```

This is useful when you want to run the tests locally without setting up all the
external dependencies. The script will automatically exclude tests that require
external services.

### Parallel Test Execution

To speed up test execution, you can run tests in parallel:

```bash
python scripts/ci.py --parallel 4
```

This will use 4 processes to run the tests.

### Python Version

You can specify a Python version to use:

```bash
python scripts/ci.py --python-version 3.10
```

Or specify a path to a Python executable:

```bash
python scripts/ci.py --python-path /path/to/python
```

### Dry Run

To see what commands would be executed without actually running them:

```bash
python scripts/ci.py --dry-run
```

## GitHub Actions Workflow

The CI script is also used in GitHub Actions workflows, defined in
`.github/workflows/ci.yml`. The workflow runs on push to main, pull requests to
main, and can be triggered manually.

The workflow includes the following jobs:

- **test**: Runs the full CI script on multiple Python versions (3.10, 3.11,
  3.12)
- **lint**: Runs only linting and formatting checks
- **type-check**: Runs only type checking
- **integration**: Runs only integration tests
- **coverage**: Runs tests with coverage reporting and uploads to Codecov

## Adding New Checks

To add new checks to the CI script:

1. Add a new method to the `CIRunner` class in `scripts/ci.py`
2. Call the method from the `run_all` method
3. Add the result to the `results` list
4. Add any necessary command-line options to the `parse_args` function
5. Update the `REQUIRED_DEPS` dictionary with any new dependencies
6. If the check requires external dependencies, update the `EXTERNAL_DEPS_FILES`
   list

## Troubleshooting

If you encounter issues with the CI script:

- Make sure you have all the required dependencies installed:
  `uv sync --extra all`
- For integration tests, you may need to have Docker running if you're using
  testcontainers
- Try running specific checks individually to isolate the issue
- Use the `--skip-external-deps` option to skip tests that require external
  dependencies
- Check the output for missing dependencies and install them as needed

### Common Issues

1. **Missing Dependencies**: The script will attempt to install missing
   dependencies automatically, but if it fails, you'll need to install them
   manually.

2. **External Dependencies**: Tests that require external services like
   databases will fail if those services are not available. Use
   `--skip-external-deps` to skip these tests.

3. **Type Checking Errors**: The type checking step may fail due to missing type
   stubs for dependencies. You can install these with
   `uv pip install types-<package>`.

4. **Docker Not Running**: If you're running integration tests that use
   testcontainers, make sure Docker is running on your system.
