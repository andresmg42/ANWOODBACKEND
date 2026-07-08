def test_login_success(client):
    response = client.post(
        "/token",
        data={"username": "admin", "password": "adminpass"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_wrong_password(client):
    response = client.post(
        "/token",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


def test_login_unknown_user(client):
    response = client.post(
        "/token",
        data={"username": "nobody", "password": "any"},
    )

    assert response.status_code == 401


def test_protected_route_without_token(client):
    response = client.get("/users")

    assert response.status_code == 401


def test_protected_route_with_invalid_token(client):
    response = client.get(
        "/users",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
