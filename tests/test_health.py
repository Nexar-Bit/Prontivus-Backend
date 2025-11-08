"""
Health check endpoint tests
"""
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
@pytest.mark.unit
async def test_root_endpoint():
    """Test root health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_health_endpoint():
    """Test detailed health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Prontivus API"
        assert data["version"] == "1.0.0"

