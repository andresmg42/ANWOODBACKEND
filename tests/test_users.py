def test_create_user(client):
    response = client.post(
        "/users",
        json={
            "username": "new_user",
            "email": "new@test.com",
            "password": "secret123",
            "full_name": "New User",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "new_user"
    assert data["email"] == "new@test.com"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_user_duplicate_username(client):
    payload = {
        "username": "duplicate_user",
        "email": "dup@test.com",
        "password": "secret123",
    }
    first = client.post("/users", json=payload)
    second = client.post("/users", json=payload)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Username already exisits"


def test_list_users_requires_auth(client):
    response = client.get("/users")

    assert response.status_code == 401


def test_list_users_as_admin(client, admin_headers):
    response = client.get("/users", headers=admin_headers)

    assert response.status_code == 200
    usernames = {user["username"] for user in response.json()}
    assert "admin" in usernames
    assert "regular_user" in usernames


def test_list_users_as_regular_user(client, user_headers):
    response = client.get("/users", headers=user_headers)

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_delete_user_forbidden_for_regular_user(client, user_headers):
    create_response = client.post(
        "/users",
        json={
            "username": "protected_user",
            "email": "protected@test.com",
            "password": "secret123",
        },
    )
    user_id = create_response.json()["id"]

    response = client.patch(f"/users/{user_id}/delete", headers=user_headers)

    assert response.status_code == 403


def test_get_user_by_id(client, admin_headers):
    users_response = client.get("/users", headers=admin_headers)
    admin_user = next(
        user for user in users_response.json() if user["username"] == "admin"
    )

    response = client.get(f"/users/{admin_user['id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_get_user_not_found(client, admin_headers):
    response = client.get("/users/99999", headers=admin_headers)

    assert response.status_code == 404


def test_soft_delete_user(client, admin_headers):
    create_response = client.post(
        "/users",
        json={
            "username": "to_delete",
            "email": "delete@test.com",
            "password": "secret123",
        },
    )
    user_id = create_response.json()["id"]

    delete_response = client.patch(
        f"/users/{user_id}/delete",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200
    assert "deleted successfully" in delete_response.json()["message"]
