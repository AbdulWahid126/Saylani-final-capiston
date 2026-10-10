import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AI Trading Copilot"
    assert data["version"] == "0.1.0"
    assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "ai-trading-copilot-backend"
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert "timestamp" in data
    assert data["database"]["status"] == "healthy"
    assert isinstance(data["mt5_terminal_detected"], bool)
