# Stream Sniper Test Suite

This directory contains comprehensive tests for the Stream Sniper application, covering all major components and workflows.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── README.md               # This file
├── __init__.py             # Test package initialization
├── unit/                   # Unit tests for individual components
│   ├── __init__.py
│   ├── api/                # API endpoint tests
│   │   └── test_api.py
│   ├── collector/          # Data collection component tests
│   │   └── test_chat_processor.py
│   ├── database/           # Database gateway tests
│   │   ├── test_creator_table_gateway.py
│   │   ├── test_decorators.py
│   │   └── test_stream_table_gateway.py
│   └── utils/              # Utility function tests
│       └── test_utils.py
├── integration/            # Integration tests for complete workflows
│   ├── __init__.py
│   ├── test_api_workflows.py
│   └── test_database_operations.py
└── fixtures/               # Test data and helper functions
    ├── __init__.py
    └── sample_data.py
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **API Tests**: Test FastAPI endpoints with mocked dependencies
- **Database Tests**: Test database gateway functions with real/mocked databases
- **Collector Tests**: Test chat processing and data collection components
- **Utils Tests**: Test utility functions for datetime parsing and other helpers

### Integration Tests (`tests/integration/`)
- **Database Operations**: Test complete database workflows with real database
- **API Workflows**: Test end-to-end API functionality with database integration

### Test Fixtures (`tests/fixtures/`)
- **Sample Data**: Standardized test data for creators, streams, chatters, and messages
- **Helper Functions**: Utilities for creating test data and validating results

## Running Tests

### Prerequisites

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup** (for integration tests):
   - PostgreSQL server running
   - Test database configured (see environment variables below)

### Environment Variables

For integration tests that use a real database, set these environment variables:

```bash
export TEST_DB_HOST=localhost
export TEST_DB_NAME=test_stream_sniper
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=password
export TEST_DB_PORT=5432
```

Or create a `.env.test` file:
```
TEST_DB_HOST=localhost
TEST_DB_NAME=test_stream_sniper
TEST_DB_USER=postgres
TEST_DB_PASSWORD=password
TEST_DB_PORT=5432
```

### Basic Test Commands

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=stream_sniper --cov-report=term-missing

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/api/test_api.py

# Run specific test function
pytest tests/unit/api/test_api.py::TestChattersEndpoints::test_get_chatter_messages_success
```

### Advanced Test Options

```bash
# Generate HTML coverage report
pytest --cov=stream_sniper --cov-report=html

# Run tests in parallel (if pytest-xdist installed)
pytest -n auto

# Run tests with profiling
pytest --profile

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run only tests marked with specific marker
pytest -m "not slow"
```

## Test Configuration

### Pytest Configuration (`pyproject.toml`)

The project includes comprehensive pytest configuration:

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --cov=stream_sniper --cov-report=term-missing"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Test Markers

You can add custom markers to categorize tests:

```python
# Mark slow tests
@pytest.mark.slow
def test_large_dataset_processing():
    pass

# Mark tests that require database
@pytest.mark.database
def test_database_integration():
    pass
```

## Mock Strategy

### Database Mocking
- **Unit Tests**: Use mocked database connections and cursors
- **Integration Tests**: Use real test database with transaction rollback
- **Fixtures**: Provide both mocked and real database setups

### External Service Mocking
- **Twitch API**: Mocked in unit tests to avoid external dependencies
- **Chat Downloader**: Mocked to provide controlled test data
- **File System**: Mocked where appropriate to avoid side effects

## Test Data Management

### Sample Data (`fixtures/sample_data.py`)
- Standardized test data for consistency across tests
- Unicode test data for internationalization testing
- Performance test data generators for load testing
- Error condition data for edge case testing

### Database Test Data
- Each test starts with clean database state
- Helper functions for creating related test data
- Automatic cleanup between tests

## Coverage Requirements

The enforced overall coverage floor is **62%**. This is the current ratchet: CI
must not regress below it, and the value should only move upward as coverage is
added. Longer-term target coverage levels are:
- **Overall**: > 85%
- **API Endpoints**: > 90%
- **Database Gateways**: > 95%
- **Critical Business Logic**: > 95%

## Continuous Integration

### GitHub Actions
```yaml
- name: Run Tests
  run: |
    uv run pytest --cov=stream_sniper --cov-report=xml
    
- name: Upload Coverage
  uses: codecov/codecov-action@v5
  with:
    fail_ci_if_error: true
```

## Test Development Guidelines

### Writing Good Tests

1. **Test Names**: Use descriptive names that explain what is being tested
   ```python
   def test_get_chatter_messages_returns_correct_format_when_chatter_exists():
   ```

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_example():
       # Arrange
       mock_data = create_test_data()
       
       # Act
       result = function_under_test(mock_data)
       
       # Assert
       assert result == expected_value
   ```

3. **Test One Thing**: Each test should verify one specific behavior

4. **Use Fixtures**: Leverage pytest fixtures for common setup

5. **Mock External Dependencies**: Don't test external services

### Test Maintenance

- Keep tests simple and focused
- Update tests when changing implementation
- Remove obsolete tests
- Ensure tests are deterministic (no random behavior)
- Use meaningful assertion messages

## Debugging Tests

### Common Issues

1. **Test Database Not Available**:
   - Check PostgreSQL is running
   - Verify connection parameters
   - Ensure test database exists

2. **Import Errors**:
   - Check PYTHONPATH includes project root
   - Verify all __init__.py files exist

3. **Fixture Conflicts**:
   - Check fixture scopes (session, function, etc.)
   - Ensure proper cleanup in fixtures

### Debugging Commands

```bash
# Run tests with pdb on failure
pytest --pdb

# Print all output (don't capture)
pytest -s

# Run specific test with verbose output
pytest -v -s tests/unit/api/test_api.py::test_specific_function
```

## Performance Testing

While not included in the current implementation, consider adding:

- Load tests for API endpoints
- Database performance tests with large datasets
- Memory usage profiling
- Concurrent access testing

## Security Testing

Consider adding tests for:

- SQL injection prevention
- Input validation
- Authentication/authorization (when implemented)
- Data sanitization

## Contributing to Tests

When adding new features:

1. Write tests first (TDD approach)
2. Ensure both positive and negative test cases
3. Add integration tests for new workflows
4. Update test documentation
5. Maintain test coverage levels

## Test Documentation Standards

- Document complex test scenarios
- Explain non-obvious mocking strategies
- Provide examples for new test patterns
- Keep this README updated with new test categories
