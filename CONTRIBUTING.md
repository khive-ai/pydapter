# Contributing to Pydapter

Thank you for your interest in contributing to Pydapter! This document provides
guidelines and instructions for contributing to the project.

## Development Environment Setup

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/your-username/pydapter.git
   cd pydapter
   ```

3. Set up a development environment:

   ```bash
   # Using uv (recommended)
   uv pip install -e ".[dev,all]"

   # Or using pip
   pip install -e ".[dev,all]"
   ```

4. Install pre-commit hooks:

   ```bash
   pre-commit install
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following the project's coding standards

3. Run the CI script locally to ensure all tests pass:

   ```bash
   python scripts/ci.py
   ```

4. Commit your changes using conventional commit messages:

   ```bash
   git commit -m "feat: add new feature"
   ```

5. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a pull request on GitHub

## Continuous Integration

The project uses a comprehensive CI system that runs:

- Linting checks (using ruff)
- Code formatting checks (using ruff format)
- Type checking (using mypy)
- Unit tests (using pytest)
- Integration tests (using pytest)
- Coverage reporting
- Documentation validation (using markdownlint and markdown-link-check)

You can run the CI script locally with various options:

```bash
# Run all checks
python scripts/ci.py

# Skip integration tests (which require Docker)
python scripts/ci.py --skip-integration

# Run only documentation validation
python scripts/ci.py --only docs

# Run only linting and formatting checks
python scripts/ci.py --skip-unit --skip-integration --skip-coverage --skip-docs

# Run tests in parallel
python scripts/ci.py --parallel 4
```

For more information, see [the CI documentation](ci.md).

## Code Style

This project follows these coding standards:

- Code formatting with [ruff format](https://docs.astral.sh/ruff/formatter/)
- Linting with [ruff](https://docs.astral.sh/ruff/)
- Type annotations for all functions and classes
- Comprehensive docstrings in
  [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Test coverage for all new features

## Testing

All new features and bug fixes should include tests. The project uses pytest for
testing:

```bash
# Run all tests
uv run pytest

# Run specific tests
uv run pytest tests/test_specific_file.py

# Run with coverage
uv run pytest --cov=pydapter
```

## Documentation

Documentation is written in Markdown and built with MkDocs using a hybrid
approach that combines auto-generated API references with enhanced manual
content.

### Documentation Standards

All documentation must follow these standards:

1. **Markdown Quality**: All markdown files must pass `markdownlint` validation
2. **Link Integrity**: All internal and external links must be valid
3. **API Documentation**: Use the hybrid approach with enhanced manual content
4. **Code Examples**: Include working code examples with proper syntax
   highlighting
5. **Cross-References**: Link related concepts and maintain navigation
   consistency

### Validation Tools

The project uses automated validation tools:

- **markdownlint**: Ensures consistent markdown formatting
- **markdown-link-check**: Validates all links in documentation
- **Pre-commit hooks**: Automatic validation before commits

### Writing Documentation

When contributing documentation:

1. **API Reference**: Follow the pattern established in `docs/api/protocols.md`
   and `docs/api/core.md`
2. **Manual Enhancement**: Add examples, best practices, and cross-references
   beyond basic API extraction
3. **User Personas**: Consider different user needs (new users, API users,
   contributors)
4. **Code Examples**: Provide complete, runnable examples
5. **Navigation**: Ensure proper cross-linking between related sections

### Documentation Workflow

```bash
# Preview documentation locally
uv run mkdocs serve

# Validate documentation
python scripts/ci.py --only docs

# Check specific files
markdownlint docs/**/*.md
markdown-link-check docs/api/core.md --config .markdownlinkcheck.json

# Fix common issues automatically (when possible)
markdownlint --fix docs/**/*.md
```

### Documentation Structure

- `docs/api/`: API reference documentation (hybrid approach)
- `docs/tutorials/`: Step-by-step guides
- `docs/`: General guides and concepts
- Examples should be complete and testable
- Cross-references should use relative links

Then open http://127.0.0.1:8000/ in your browser to preview changes.

## Pull Request Process

1. Ensure your code passes all CI checks
2. Update documentation if necessary
3. Add tests for new features
4. Make sure your PR description clearly describes the changes and their purpose
5. Wait for review and address any feedback

## License

By contributing to Pydapter, you agree that your contributions will be licensed
under the project's MIT License.
