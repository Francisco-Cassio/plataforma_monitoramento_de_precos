import uuid
from httpx import AsyncClient

# Teste de registro de usuário
async def test_register_success(client: AsyncClient):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@exemplo.com"
    payload = {
        "email": unique_email,
        "password": "SenhaForte123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == unique_email
    assert "id" in data
    assert "password" not in data


# Não deve permitir e-mails duplicados
async def test_register_duplicate_email(client: AsyncClient):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@exemplo.com"
    payload = {
        "email": unique_email,
        "password": "SenhaForte123!",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "Email já cadastrado" in res2.json()["detail"]


async def test_login_success(client: AsyncClient):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@exemplo.com"
    password = "SenhaForte123!"
    await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password},
    )

    login_data = {
        "username": unique_email,
        "password": password,
    }
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    assert login_resp.status_code == 200

    data = login_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# Rejeita senha incorreta com 401
async def test_login_invalid_password(client: AsyncClient):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@exemplo.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "Correta123!"},
    )

    login_data = {
        "username": unique_email,
        "password": "SenhaErrada!",
    }
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    assert login_resp.status_code == 401


async def test_get_current_user_me(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "email" in data
    assert data["is_active"] is True


# Bloqueia chamadas sem token
async def test_get_current_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401