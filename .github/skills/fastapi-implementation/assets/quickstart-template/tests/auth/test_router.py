"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient):
    """Test registration with duplicate username."""
    user_data = {"username": "testuser", "email": "test@example.com", "password": "SecurePass123!"}

    # First registration
    response1 = await client.post("/api/auth/register", json=user_data)
    assert response1.status_code == 201

    # Duplicate registration
    response2 = await client.post("/api/auth/register", json=user_data)
    assert response2.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """Test user login."""
    # Register user
    await client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "SecurePass123!"},
    )

    # Login
    response = await client.post(
        "/api/auth/login", json={"username": "testuser", "password": "SecurePass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/auth/login", json={"username": "nonexistent", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user with token."""
    # Register user
    await client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "SecurePass123!"},
    )

    # Login
    login_response = await client.post(
        "/api/auth/login", json={"username": "testuser", "password": "SecurePass123!"}
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test getting current user without token."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
