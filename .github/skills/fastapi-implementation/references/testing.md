# Testing FastAPI Applications

## Overview

FastAPI testing leverages pytest and httpx's AsyncClient for async testing. Always use async from the start.

## Basic Setup

### Test Dependencies

```bash
pip install pytest pytest-asyncio httpx
```

### Configuration

```python
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_main.py         # App-level tests
├── auth/
│   ├── __init__.py
│   ├── conftest.py      # Auth-specific fixtures
│   ├── test_router.py   # Auth endpoint tests
│   └── test_service.py  # Auth service tests
└── posts/
    ├── __init__.py
    ├── conftest.py
    ├── test_router.py
    └── test_service.py
```

## AsyncClient Setup

### Basic Client Fixture

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.fixture
async def client():
    """Provide async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
```

### Usage in Tests

```python
# tests/test_main.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "password" not in data  # Sensitive data not returned
```

## Database Testing

### Test Database Fixture

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base, get_db
from src.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def client(test_db: AsyncSession):
    """Override database dependency with test database."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
```

### Using Test Database

```python
@pytest.mark.asyncio
async def test_create_and_get_user(client: AsyncClient, test_db: AsyncSession):
    # Create user
    create_response = await client.post(
        "/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    # Verify in database
    from src.auth.models import User
    user = await test_db.get(User, user_id)
    assert user is not None
    assert user.username == "testuser"

    # Get user via API
    get_response = await client.get(f"/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["username"] == "testuser"
```

## Authentication Testing

### Auth Token Fixture

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def auth_token(client: AsyncClient):
    """Create user and return auth token."""
    # Register user
    await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
    )

    # Login
    response = await client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "SecurePass123!"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
async def authenticated_client(client: AsyncClient, auth_token: str):
    """Provide client with auth header."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client
```

### Testing Protected Endpoints

```python
@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client: AsyncClient):
    """Test that protected endpoint requires authentication."""
    response = await client.get("/api/protected")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_endpoint_with_auth(authenticated_client: AsyncClient):
    """Test protected endpoint with valid token."""
    response = await authenticated_client.get("/api/protected")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_admin_endpoint_requires_admin_role(authenticated_client: AsyncClient):
    """Test admin endpoint rejects regular user."""
    response = await authenticated_client.get("/api/admin/users")
    assert response.status_code == 403  # Forbidden
```

## Testing Patterns

### Testing CRUD Operations

```python
@pytest.mark.asyncio
class TestPostCRUD:
    """Test post CRUD operations."""

    async def test_create_post(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post(
            "/posts",
            json={
                "title": "Test Post",
                "content": "This is a test post content."
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Post"
        assert "id" in data
        return data["id"]

    async def test_get_post(self, authenticated_client: AsyncClient):
        # Create post
        create_response = await authenticated_client.post(
            "/posts",
            json={"title": "Test", "content": "Content"}
        )
        post_id = create_response.json()["id"]

        # Get post
        response = await authenticated_client.get(f"/posts/{post_id}")
        assert response.status_code == 200
        assert response.json()["id"] == post_id

    async def test_update_post(self, authenticated_client: AsyncClient):
        # Create post
        create_response = await authenticated_client.post(
            "/posts",
            json={"title": "Original", "content": "Content"}
        )
        post_id = create_response.json()["id"]

        # Update post
        response = await authenticated_client.put(
            f"/posts/{post_id}",
            json={"title": "Updated", "content": "New content"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    async def test_delete_post(self, authenticated_client: AsyncClient):
        # Create post
        create_response = await authenticated_client.post(
            "/posts",
            json={"title": "To Delete", "content": "Content"}
        )
        post_id = create_response.json()["id"]

        # Delete post
        response = await authenticated_client.delete(f"/posts/{post_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = await authenticated_client.get(f"/posts/{post_id}")
        assert get_response.status_code == 404
```

### Testing Validation

```python
@pytest.mark.asyncio
async def test_create_user_with_invalid_email(client: AsyncClient):
    """Test validation error for invalid email."""
    response = await client.post(
        "/users",
        json={
            "username": "testuser",
            "email": "not-an-email",  # Invalid
            "password": "SecurePass123!"
        }
    )
    assert response.status_code == 422
    error = response.json()
    assert "email" in str(error).lower()

@pytest.mark.asyncio
async def test_create_user_with_weak_password(client: AsyncClient):
    """Test password validation."""
    response = await client.post(
        "/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak"  # Too short
        }
    )
    assert response.status_code == 422
    error = response.json()
    assert "password" in str(error).lower()

@pytest.mark.asyncio
async def test_create_user_with_duplicate_email(client: AsyncClient):
    """Test unique constraint on email."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!"
    }

    # Create first user
    response1 = await client.post("/users", json=user_data)
    assert response1.status_code == 201

    # Try to create with same email
    user_data["username"] = "different"
    response2 = await client.post("/users", json=user_data)
    assert response2.status_code == 409  # Conflict
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_get_nonexistent_post(client: AsyncClient):
    """Test 404 for nonexistent resource."""
    from uuid import uuid4
    fake_id = uuid4()
    response = await client.get(f"/posts/{fake_id}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_post_unauthorized(client: AsyncClient, authenticated_client: AsyncClient):
    """Test that user cannot update another user's post."""
    # User 1 creates post
    response = await authenticated_client.post(
        "/posts",
        json={"title": "User 1 Post", "content": "Content"}
    )
    post_id = response.json()["id"]

    # User 2 tries to update (need separate auth fixture for this)
    # For simplicity, use unauthenticated client
    response = await client.put(
        f"/posts/{post_id}",
        json={"title": "Hacked!"}
    )
    assert response.status_code == 401
```

### Parametrized Tests

```python
import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize("username,email,password,expected_status", [
    ("valid", "valid@example.com", "SecurePass123!", 201),
    ("a", "valid@example.com", "SecurePass123!", 422),  # Username too short
    ("valid", "not-email", "SecurePass123!", 422),  # Invalid email
    ("valid", "valid@example.com", "weak", 422),  # Weak password
])
async def test_user_registration_validation(
    client: AsyncClient,
    username: str,
    email: str,
    password: str,
    expected_status: int
):
    response = await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )
    assert response.status_code == expected_status
```

## Mocking Dependencies

### Mock External Services

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_send_email(client: AsyncClient):
    """Test email sending without actually sending."""
    with patch('src.email.service.send_email') as mock_send:
        mock_send.return_value = AsyncMock(return_value=True)

        response = await client.post(
            "/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 201
        mock_send.assert_called_once()
```

### Mock Database Operations

```python
@pytest.mark.asyncio
async def test_get_user_service():
    """Test service layer with mocked database."""
    from unittest.mock import AsyncMock
    from src.auth.service import get_user_by_id
    from src.auth.models import User

    # Mock database session
    mock_db = AsyncMock()
    mock_user = User(id=1, username="testuser", email="test@example.com")
    mock_db.get.return_value = mock_user

    # Call service
    result = await get_user_by_id(mock_db, user_id=1)

    # Verify
    assert result.username == "testuser"
    mock_db.get.assert_called_once_with(User, 1)
```

## Testing WebSockets

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_websocket_connection(client: AsyncClient):
    """Test WebSocket endpoint."""
    async with client.websocket_connect("/ws") as websocket:
        # Send message
        await websocket.send_json({"message": "Hello"})

        # Receive response
        data = await websocket.receive_json()
        assert data["message"] == "Hello"

@pytest.mark.asyncio
async def test_websocket_authentication(client: AsyncClient, auth_token: str):
    """Test authenticated WebSocket."""
    async with client.websocket_connect(
        f"/ws?token={auth_token}"
    ) as websocket:
        await websocket.send_json({"action": "get_data"})
        data = await websocket.receive_json()
        assert "data" in data
```

## Testing Background Tasks

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_background_task(client: AsyncClient):
    """Test endpoint that triggers background task."""
    response = await client.post(
        "/process-data",
        json={"data": "test"}
    )
    assert response.status_code == 202  # Accepted

    # Wait for background task to complete
    await asyncio.sleep(0.5)

    # Verify task result
    status_response = await client.get("/task-status")
    assert status_response.json()["status"] == "completed"
```

## Test Fixtures Best Practices

### Reusable Data Fixtures

```python
# tests/conftest.py
import pytest
from uuid import uuid4

@pytest.fixture
def sample_user_data():
    """Provide sample user data."""
    return {
        "username": f"user_{uuid4().hex[:8]}",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!"
    }

@pytest.fixture
def sample_post_data():
    """Provide sample post data."""
    return {
        "title": "Test Post",
        "content": "This is test content for the post.",
        "tags": ["test", "sample"]
    }
```

### Factory Fixtures

```python
@pytest.fixture
async def user_factory(client: AsyncClient):
    """Factory for creating test users."""
    created_users = []

    async def create_user(**kwargs):
        default_data = {
            "username": f"user_{uuid4().hex[:8]}",
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "password": "SecurePass123!"
        }
        default_data.update(kwargs)

        response = await client.post("/users", json=default_data)
        user = response.json()
        created_users.append(user["id"])
        return user

    yield create_user

    # Cleanup
    for user_id in created_users:
        await client.delete(f"/users/{user_id}")

# Usage
@pytest.mark.asyncio
async def test_multiple_users(user_factory):
    user1 = await user_factory(username="alice")
    user2 = await user_factory(username="bob")
    assert user1["username"] == "alice"
    assert user2["username"] == "bob"
```

## Coverage

### Setup Coverage

```bash
pip install pytest-cov
```

### Run with Coverage

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Show coverage report
open htmlcov/index.html
```

### Coverage Configuration

```ini
# .coveragerc or pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Performance Testing

### Load Testing with Locust

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before tests."""
        response = self.client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "password"
            }
        )
        self.token = response.json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    @task(3)
    def get_posts(self):
        """Get posts list (3x weight)."""
        self.client.get("/posts")

    @task(1)
    def create_post(self):
        """Create post (1x weight)."""
        self.client.post(
            "/posts",
            json={
                "title": "Load Test Post",
                "content": "Content"
            }
        )

# Run: locust -f tests/load/locustfile.py
```

## Best Practices

✅ **Do:**

- Always use AsyncClient for testing
- Set up separate test database
- Use fixtures for common test data
- Test both success and failure cases
- Mock external services
- Test validation and error handling
- Organize tests to mirror source structure
- Use parametrized tests for multiple scenarios
- Clean up test data after tests
- Measure and maintain test coverage

❌ **Don't:**

- Use production database for tests
- Leave test data in database
- Skip testing error cases
- Hardcode test data that could conflict
- Test implementation details
- Make tests depend on execution order
- Ignore slow tests (optimize or move to integration suite)
- Mock everything (test real integrations when possible)

## Test Organization

### Unit Tests

Test individual functions/methods in isolation:

```python
# tests/auth/test_service.py
async def test_hash_password():
    from src.auth.service import hash_password
    hashed = await hash_password("password123")
    assert hashed != "password123"
    assert len(hashed) > 20
```

### Integration Tests

Test multiple components working together:

```python
# tests/auth/test_router.py
async def test_full_registration_flow(client: AsyncClient):
    # Register -> Login -> Access Protected Resource
    pass
```

### End-to-End Tests

Test complete user workflows:

```python
# tests/e2e/test_user_journey.py
async def test_complete_user_journey(client: AsyncClient):
    # Register -> Verify Email -> Login -> Create Post -> Comment -> Logout
    pass
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/auth/test_router.py

# Run specific test
pytest tests/auth/test_router.py::test_login

# Run with verbosity
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run only failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_user"

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Stop on first failure
pytest -x
```

## Summary

Effective testing in FastAPI requires:

1. **AsyncClient** for all HTTP tests
2. **Test database** separate from production
3. **Fixtures** for reusable test data
4. **Mocking** for external dependencies
5. **Coverage** measurement and maintenance
6. **Multiple test levels** (unit, integration, e2e)

Well-tested applications are easier to maintain, refactor, and scale with confidence.
