def test_get_cart_creates_empty_cart(client, user_headers):
    response = client.get("/cart", headers=user_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert "id" in data
    assert "user_id" in data


def test_add_item_to_cart(client, user_headers):
    piezas_response = client.get("/piezas")
    pieza_id = piezas_response.json()[0]["id"]

    response = client.post(
        "/cart/items",
        headers=user_headers,
        json={"wood_piece_id": pieza_id, "cantidad": 2},
    )

    assert response.status_code == 201
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["wood_piece_id"] == pieza_id
    assert items[0]["cantidad"] == 2


def test_cart_requires_auth(client):
    response = client.get("/cart")

    assert response.status_code == 401
