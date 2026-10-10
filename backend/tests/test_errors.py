import pytest
from httpx import AsyncClient

from app.core.logging import SecretMaskingFilter


def test_secret_masking_filter():
    f = SecretMaskingFilter()
    masked = f.mask_secrets("User login attempt with password=supersecretpass123")
    assert "supersecretpass123" not in masked
    assert "***REDACTED***" in masked

    bearer_masked = f.mask_secrets(
        "Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    )
    assert "***REDACTED***" in bearer_masked


@pytest.mark.asyncio
async def test_404_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
