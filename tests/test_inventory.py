def test_list_lotes_requires_auth(client):
    response = client.get("/lotes")

    assert response.status_code == 401


def test_list_lotes_as_admin(client, admin_headers):
    response = client.get("/lotes", headers=admin_headers)

    assert response.status_code == 200
    lotes = response.json()
    assert len(lotes) >= 1
    assert lotes[0]["codigo_lote"] == "LOTE-001"
    assert len(lotes[0]["proveedores"]) >= 1
    assert lotes[0]["proveedores"][0]["nombre"] == "Proveedor Semilla"


def test_list_proveedores_as_admin(client, admin_headers):
    response = client.get("/proveedores", headers=admin_headers)

    assert response.status_code == 200
    assert any(p["nombre"] == "Proveedor Semilla" for p in response.json())


def test_create_lote_with_proveedores(client, admin_headers):
    proveedores_response = client.get("/proveedores", headers=admin_headers)
    proveedor_id = proveedores_response.json()[0]["id"]

    response = client.post(
        "/lotes",
        headers=admin_headers,
        json={
            "codigo_lote": "LOTE-TEST-001",
            "costo_total": "50000",
            "proveedor_ids": [proveedor_id],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["codigo_lote"] == "LOTE-TEST-001"
    assert len(data["proveedores"]) == 1
    assert data["proveedores"][0]["id"] == proveedor_id


def test_create_proveedor_as_admin(client, admin_headers):
    response = client.post(
        "/proveedores",
        headers=admin_headers,
        json={
            "nombre": "Proveedor Test",
            "telefono": "3100000000",
        },
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Proveedor Test"


def test_create_lote_forbidden_for_regular_user(client, user_headers):
    response = client.post(
        "/lotes",
        headers=user_headers,
        json={
            "codigo_lote": "LOTE-TEST-002",
        },
    )

    assert response.status_code == 403
