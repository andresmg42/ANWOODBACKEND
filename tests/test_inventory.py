def test_list_lotes_requires_auth(client):
    response = client.get("/lotes")

    assert response.status_code == 401


def test_list_lotes_as_admin(client, admin_headers):
    response = client.get("/lotes", headers=admin_headers)

    assert response.status_code == 200
    lotes = response.json()
    assert len(lotes) >= 1
    assert lotes[0]["codigo_lote"] == "LOTE-001"


def test_create_lote_as_admin(client, admin_headers):
    response = client.post(
        "/lotes",
        headers=admin_headers,
        json={
            "codigo_lote": "LOTE-TEST-001",
            "proveedor": "Proveedor Test",
            "costo_total": "50000",
        },
    )

    assert response.status_code == 201
    assert response.json()["codigo_lote"] == "LOTE-TEST-001"


def test_create_lote_forbidden_for_regular_user(client, user_headers):
    response = client.post(
        "/lotes",
        headers=user_headers,
        json={
            "codigo_lote": "LOTE-TEST-002",
            "proveedor": "Proveedor Test",
        },
    )

    assert response.status_code == 403
