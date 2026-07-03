import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_raises_409(client: AsyncClient):
    payload = {"email": "bob@example.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "secret"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "secret"},
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dan@example.com", "password": "correct"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "dan@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "pw"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "eve@example.com", "password": "pw"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "eve@example.com"


@pytest.mark.asyncio
async def test_refresh(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "frank@example.com", "password": "pw"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "frank@example.com", "password": "pw"},
    )
    refresh_token = login.json()["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_admin_endpoint_forbidden_for_regular_user(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "grace@example.com", "password": "pw", "role": "user"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "grace@example.com", "password": "pw"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoint_accessible_for_admin(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "henry@example.com", "password": "pw", "role": "admin"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "henry@example.com", "password": "pw"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
