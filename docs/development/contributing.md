# Contributing Guide

This document provides guidelines for contributing to the Brokkoli Plant Integration project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Run tests to ensure everything works

## Development Environment Setup

### Prerequisites

- Python 3.8+
- Git
- Code editor (VS Code recommended)

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/homeassistant-brokkoli.git
   cd homeassistant-brokkoli
   ```

2. Install dependencies (if any specific ones are needed)

3. Run tests to verify setup:
   ```bash
   python tests/run_tests.py
   ```

## Code Standards

### Python Style

Follow PEP 8 guidelines for Python code:
- Use 4 spaces for indentation
- Limit lines to 88 characters (Black format)
- Use descriptive variable and function names
- Include docstrings for public functions and classes

### Documentation

- Update documentation when adding new features
- Write clear, concise docstrings
- Include examples when helpful
- Keep README files up to date

### Testing

All contributions must include appropriate tests:
- Unit tests for new functions
- Integration tests for new components
- Update existing tests if functionality changes
- Ensure all tests pass before submitting

## Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Add tests for new functionality
3. Update documentation as needed
4. Follow the code style guidelines
5. Write a clear, descriptive commit message

### Pull Request Guidelines

1. Fork the repository and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue that pull request!

### Commit Messages

Write clear, concise commit messages:
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Testing Guidelines

### Test Structure

Follow the existing test structure:
- Unit tests in the `tests/unit` directory
- Integration tests in the `tests/integration` directory
- Tent-specific tests in the `tests/tent_specific` directory

### Test Implementation

- Use the existing module loading pattern
- Mock external dependencies appropriately
- Test both success and failure cases
- Use descriptive test function names
- Include comments for complex test scenarios

### Test Coverage

Aim for comprehensive test coverage:
- Happy path scenarios
- Error conditions
- Edge cases
- Boundary conditions

## Code Review Process

All submissions require review. We use GitHub pull requests for this process.

### Review Criteria

1. Code quality and style
2. Test coverage and quality
3. Documentation updates
4. Adherence to architectural patterns
5. Performance considerations

### Response to Feedback

- Make requested changes promptly
- Ask questions if feedback is unclear
- Discuss alternative approaches if needed
- Be open to suggestions for improvement

## Reporting Issues

### Bug Reports

When reporting bugs, include:
- A clear description of the issue
- Steps to reproduce
- Expected vs. actual behavior
- Environment information (Python version, OS, etc.)
- Relevant logs or error messages

### Feature Requests

For feature requests, include:
- A clear description of the desired functionality
- Use cases for the feature
- Potential implementation approaches
- Any alternatives considered

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Welcome newcomers
- Value diverse perspectives

### Communication

- Use clear, professional language
- Be patient with newcomers
- Provide context for suggestions
- Explain reasoning behind decisions

## Additional Resources

- [Testing Documentation](testing.md)
- [Architecture Documentation](architecture.md)
- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)