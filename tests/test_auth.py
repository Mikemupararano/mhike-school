import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "fake@test.com",
            "password": "wrong",
            "school_id": 1,
        },
    )

    assert response.status_code in (400, 401, 422)
