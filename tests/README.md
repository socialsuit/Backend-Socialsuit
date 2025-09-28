# Social Suit Testing Documentation

## Test Structure

The testing structure is organized into three main categories:

- **Unit Tests** (`tests/unit/`): Tests for individual components in isolation with mocked dependencies.
- **Edge Tests** (`tests/edge/`): Tests for edge cases and boundary conditions.
- **Integration Tests** (`tests/integration/`): Tests for interactions between multiple components.

## Running Tests

### Running All Tests

```bash
python -m pytest
```

### Running Tests by Category

```bash
# Run unit tests only
python -m pytest tests/unit/

# Run edge tests only
python -m pytest tests/edge/

# Run integration tests only
python -m pytest tests/integration/
```

### Running Tests by Marker

```bash
# Run tests marked as unit tests
python -m pytest -m unit

# Run tests marked as integration tests
python -m pytest -m integration

# Run tests for specific features
python -m pytest -m auth  # Authentication tests
python -m pytest -m scheduler  # Scheduler tests
python -m pytest -m analytics  # Analytics tests
python -m pytest -m ab_testing  # AB testing tests
python -m pytest -m post_recycler  # Post recycler tests
python -m pytest -m auto_engagement  # Auto engagement tests
```

### Running Tests with Coverage

```bash
python -m pytest --cov=app tests/
```

To generate an HTML coverage report:

```bash
python -m pytest --cov=app --cov-report=html tests/
```

The report will be available in the `htmlcov` directory.

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py`. These include:

- `async_client`: A FastAPI AsyncClient for testing async endpoints
- `client`: A FastAPI TestClient for testing synchronous endpoints
- `auth_headers`: Authentication headers for testing protected endpoints
- Various repository mocks for database isolation

## Mocking

The `tests/utils.py` file contains utility functions and classes for mocking:

- `MockDBSession`: A mock database session for testing repository classes
- Repository mocks for different data models
- Dependency override functions for FastAPI dependency injection

## Adding New Tests

When adding new tests:

1. Place unit tests in the `tests/unit/` directory
2. Place edge case tests in the `tests/edge/` directory
3. Place integration tests in the `tests/integration/` directory
4. Use appropriate markers to categorize your tests
5. Follow the naming convention: `test_*.py` for test files and `test_*` for test functions
6. Use fixtures from `conftest.py` where appropriate
7. Mock external dependencies for unit tests

## Continuous Integration

Tests are automatically run on each pull request and push to the main branch using GitHub Actions. The workflow configuration is in `.github/workflows/tests.yml`.