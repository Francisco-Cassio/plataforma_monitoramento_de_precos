import uuid
from httpx import AsyncClient

# Teste de criação de produto
async def test_create_product_success(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "url": f"https://www.mercadolivre.com.br/produto-{uuid.uuid4().hex[:6]}",
        "title": "Monitor Gamer 144Hz",
    }
    response = await client.post("/api/v1/products/", json=payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Monitor Gamer 144Hz"
    assert data["platform"] == "mercadolivre"
    assert "id" in data


# Não pode cadastrar a mesma URL duas vezes pro mesmo usuário
async def test_create_product_duplicate_url(client: AsyncClient, auth_headers: dict[str, str]):
    same_url = f"https://www.mercadolivre.com.br/produto-{uuid.uuid4().hex[:6]}"
    payload = {
        "url": same_url,
        "title": "Mouse Gamer",
    }
    res1 = await client.post("/api/v1/products/", json=payload, headers=auth_headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/products/", json=payload, headers=auth_headers)
    assert res2.status_code == 400
    assert "já está monitorando" in res2.json()["detail"]


# Se passar target_price, deve criar um alerta automaticamente
async def test_create_product_with_auto_alert(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "url": f"https://www.amazon.com.br/dp/{uuid.uuid4().hex[:6]}",
        "title": "Kindle Paperwhite",
        "target_price": "450.00",
    }
    response = await client.post("/api/v1/products/", json=payload, headers=auth_headers)
    assert response.status_code == 201

    alerts_resp = await client.get("/api/v1/alerts/", headers=auth_headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) >= 1
    assert any(float(a["target_price"]) == 450.00 for a in alerts)


# Teste de listagem de produtos do usuário
async def test_list_my_products(client: AsyncClient, auth_headers: dict[str, str]):
    await client.post(
        "/api/v1/products/",
        json={"url": f"https://www.magazineluiza.com.br/p/{uuid.uuid4().hex[:6]}", "title": "Cadeira"},
        headers=auth_headers,
    )

    response = await client.get("/api/v1/products/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# Teste de criação de alerta manual para um produto existente
async def test_create_manual_alert(client: AsyncClient, auth_headers: dict[str, str]):
    prod_resp = await client.post(
        "/api/v1/products/",
        json={"url": f"https://www.amazon.com.br/dp/{uuid.uuid4().hex[:6]}", "title": "Fone Bluetooth"},
        headers=auth_headers,
    )
    product_id = prod_resp.json()["id"]

    alert_payload = {
        "product_id": product_id,
        "target_price": "199.90",
        "condition": "<=",
    }
    response = await client.post("/api/v1/alerts/", json=alert_payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["product_id"] == product_id
    assert float(data["target_price"]) == 199.90
    assert data["condition"] == "<="


# Garante que um usuário não consiga ver produtos de outro
async def test_product_multi_tenant_isolation(client: AsyncClient, auth_headers: dict[str, str]):
    prod_resp = await client.post(
        "/api/v1/products/",
        json={"url": f"https://www.mercadolivre.com.br/p/{uuid.uuid4().hex[:6]}", "title": "Produto Secreto"},
        headers=auth_headers,
    )
    product_id = prod_resp.json()["id"]

    # Cria outro usuário
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@exemplo.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": user_b_email, "password": "OutraSenha123!"},
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        data={"username": user_b_email, "password": "OutraSenha123!"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # Usuário B não pode acessar o produto do Usuário A
    response = await client.get(f"/api/v1/products/{product_id}", headers=headers_b)
    assert response.status_code == 403
    assert "permissão" in response.json()["detail"].lower()


# Teste de deleção de produto
async def test_delete_product(client: AsyncClient, auth_headers: dict[str, str]):
    prod_resp = await client.post(
        "/api/v1/products/",
        json={"url": f"https://www.mercadolivre.com.br/p/{uuid.uuid4().hex[:6]}", "title": "Para Deletar"},
        headers=auth_headers,
    )
    product_id = prod_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/products/{product_id}", headers=auth_headers)
    assert del_resp.status_code == 204