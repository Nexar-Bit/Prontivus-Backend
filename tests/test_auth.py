"""
Authentication endpoint tests
"""
import pytest
from httpx import AsyncClient
from main import app
from tests.conftest import test_user, auth_headers


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_login_success(test_user, db_session):
    """Test successful login"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.auth
async def test_get_current_user(auth_headers):
    """Test getting current user with valid token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "role" in data

