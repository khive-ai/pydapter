# Contributing to pydapter

Thank you for your interest in contributing to pydapter! This document provides
guidelines and instructions for contributing to this project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this
project.

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ohdearquant/pydapter.git
cd pydapter

# Install development dependencies
pip install -e ".[all,dev]"

# Run tests
pytest
```

## Automated Roles

This project uses automated roles via the khive system. The role definitions are
stored in `.github/khive_modes.json`. The khive-orchestrator opens tasks and
PRs, and coordinates work between different specialized roles:

- **Orchestrator**: Coordinates tasks and manages the project workflow
- **Architect**: Designs the technical architecture
- **Researcher**: Conducts research and gathers information
- **Implementer**: Implements code based on specifications
- **Quality Reviewer**: Reviews code for quality and correctness
- **Documenter**: Creates and maintains documentation

## Pull Request Process

1. Ensure your code follows the project's coding standards
2. Update the README.md or documentation with details of changes if appropriate
3. The PR will be merged once it receives approval from maintainers

## Testing

Please ensure that your contributions include appropriate tests and maintain or
improve the current test coverage.

## License

By contributing to pydapter, you agree that your contributions will be licensed
under the project's license.
