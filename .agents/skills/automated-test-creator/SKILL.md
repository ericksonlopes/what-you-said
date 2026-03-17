---
name: automated-test-creator
description: Creates high-coverage automated tests for WhatYouSaid using pytest. Use when you need to add unit or integration tests for new features, fix bugs with reproductions, or increase project coverage.
---

# Automated Test Creator (WhatYouSaid)

This skill provides a specialized workflow and established patterns for creating robust automated tests in the WhatYouSaid ecosystem.

## Core Testing Stack
- **Framework**: `pytest`
- **API Testing**: `fastapi.testclient.TestClient`
- **Mocking**: `unittest.mock` (MagicMock, patch) and `monkeypatch`
- **Database**: In-memory SQLite using the `sqlite_memory` fixture in `tests/conftest.py`

## Structure: Test Classes & Markers
Always group tests within classes and apply a custom `@pytest.mark`.

1. **Mark the Class**: Use a descriptive marker.
2. **Register the Marker**: Add the marker description to `pytest.ini`.

```python
@pytest.mark.MyFeature
class TestMyFeature:
    def test_logic(self):
        pass
```

## Coverage Policy
Do NOT write tests for pure data structures (Models, Schemas, DTOs, Entities, Mappers). These are omitted in `.coveragerc`. Focus 100% on **Services, Use Cases, Repositories, and Routers**.

## Workflow

### 1. Analysis
- Identify the target file and lines missing coverage.
- If it's a data structure folder (e.g., `src/domain/entities`), skip it and ensure it's in `.coveragerc` `omit`.
- Determine external dependencies to mock.

### 2. Implementation
- Create the test class with the appropriate marker.
- Register the marker in `pytest.ini` if new.

#### Mocking Services in Routers
Use `app.dependency_overrides` to inject mocks into FastAPI routes.
```python
from main import app
from src.presentation.api.dependencies import get_my_service

@pytest.fixture
def mock_service():
    mock = MagicMock()
    app.dependency_overrides[get_my_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_my_service, None)
```

#### Handling Optional Dependencies (Lazy Loading)
Since Weaviate and FAISS are optional, mock them at the module level using `sys.modules`.
```python
import sys
from unittest.mock import MagicMock

def test_something(monkeypatch):
    mock_lib = MagicMock()
    monkeypatch.setitem(sys.modules, "weaviate", mock_lib)
    # Now code importing 'weaviate' inside methods won't fail
```

### 3. Database Tests
Always use the `sqlite_memory` fixture for repository or service tests that touch the DB.
```python
def test_repo_method(sqlite_memory):
    repo = MySqlRepository()
    # Repository now uses a fresh in-memory session
```

### 4. Use Case Tests
- Use `SimpleNamespace` for quick entity mocking.
- Mock all injected services in the constructor.
- Test both success and failure (Exception) paths.

## Validation Standards
- **Coverage**: Aim for 100% on the targeted file.
- **Isolation**: Tests must not require internet access or running containers.
- **Cleanliness**: Use `monkeypatch` instead of manual patching where possible to ensure automatic cleanup.

## Commands
- Run tests: `uv run pytest tests/path/to/test.py`
- Check coverage: `uv run pytest --cov=src/path/to/target --cov-report=term-missing`
