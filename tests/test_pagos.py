import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

os.environ.setdefault("MP_ACCESS_TOKEN", "TEST-fake")
os.environ.setdefault("APP_URL", "http://localhost:3000")
os.environ.setdefault("API_URL", "http://localhost:8000")

from app.models import Cart, ItemCart, Pago, User, WoodPiece


PREFERENCIA_BODY = {
    "items": [
        {
            "pieza_id": 1,
            "titulo": "Tabla de pino",
            "cantidad": 2,
            "precio_unitario": 50000,
        }
    ],
    "payer": {"name": "Juan Pérez", "email": "juan@example.com"},
}

MOCK_PREFERENCE_RESPONSE = {
    "status": 201,
    "response": {
        "id": "pref-test-123",
        "init_point": "https://www.mercadopago.com/checkout/v1/redirect?pref_id=pref-test-123",
        "sandbox_init_point": "https://sandbox.mercadopago.com/checkout/v1/redirect?pref_id=pref-test-123",
    },
}


@pytest.fixture
def mock_mp_sdk():
    with patch("app.routers.pagos.sdk") as mock_sdk:
        preference_api = MagicMock()
        payment_api = MagicMock()
        mock_sdk.preference.return_value = preference_api
        mock_sdk.payment.return_value = payment_api
        yield mock_sdk, preference_api, payment_api


def test_crear_preferencia_ok(client, user_headers, mock_mp_sdk):
    _, preference_api, _ = mock_mp_sdk
    preference_api.create.return_value = MOCK_PREFERENCE_RESPONSE

    response = client.post(
        "/pagos/preferencia",
        headers=user_headers,
        json=PREFERENCIA_BODY,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["preference_id"] == "pref-test-123"
    assert "sandbox_init_point" in data
    assert data["payment_url"] == data["sandbox_init_point"]
    preference_api.create.assert_called_once()


def test_crear_preferencia_sin_auth(client, mock_mp_sdk):
    response = client.post("/pagos/preferencia", json=PREFERENCIA_BODY)
    assert response.status_code == 401


def test_webhook_payment_approved(client, session, user_headers, mock_mp_sdk):
    _, preference_api, payment_api = mock_mp_sdk
    preference_api.create.return_value = MOCK_PREFERENCE_RESPONSE

    create_response = client.post(
        "/pagos/preferencia",
        headers=user_headers,
        json=PREFERENCIA_BODY,
    )
    assert create_response.status_code == 201

    user = session.exec(select(User).where(User.username == "regular_user")).first()
    pieza = session.exec(select(WoodPiece)).first()
    assert user is not None
    assert pieza is not None

    carrito = session.exec(select(Cart).where(Cart.user_id == user.id)).first()
    if not carrito:
        carrito = Cart(user_id=user.id)
        session.add(carrito)
        session.commit()
        session.refresh(carrito)

    item = ItemCart(carrito_id=carrito.id, wood_piece_id=pieza.id, cantidad=1)
    pieza.cantidad_reservada += 1
    session.add(item)
    session.commit()

    payment_api.get.return_value = {
        "status": 200,
        "response": {
            "id": 999001,
            "status": "approved",
            "preference_id": "pref-test-123",
            "metadata": {"user_id": user.id},
        },
    }

    webhook_response = client.post(
        "/pagos/webhook",
        json={"type": "payment", "data": {"id": "999001"}},
    )
    assert webhook_response.status_code == 200

    pago = session.exec(
        select(Pago).where(Pago.preference_id == "pref-test-123")
    ).first()
    assert pago is not None
    assert pago.status == "approved"
    assert pago.mp_payment_id == "999001"

    session.refresh(carrito)
    items = session.exec(
        select(ItemCart).where(ItemCart.carrito_id == carrito.id)
    ).all()
    assert items == []


def test_webhook_idempotente(client, user_headers, mock_mp_sdk):
    _, preference_api, payment_api = mock_mp_sdk
    preference_api.create.return_value = MOCK_PREFERENCE_RESPONSE

    client.post(
        "/pagos/preferencia",
        headers=user_headers,
        json=PREFERENCIA_BODY,
    )

    payment_api.get.return_value = {
        "status": 200,
        "response": {
            "id": 888002,
            "status": "approved",
            "preference_id": "pref-test-123",
            "metadata": {"user_id": 2},
        },
    }

    payload = {"type": "payment", "data": {"id": "888002"}}
    first = client.post("/pagos/webhook", json=payload)
    second = client.post("/pagos/webhook", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    payment_api.get.assert_called()


def test_get_pago_ok(client, user_headers, mock_mp_sdk):
    _, preference_api, _ = mock_mp_sdk
    preference_api.create.return_value = MOCK_PREFERENCE_RESPONSE

    create_response = client.post(
        "/pagos/preferencia",
        headers=user_headers,
        json=PREFERENCIA_BODY,
    )
    assert create_response.status_code == 201

    response = client.get("/pagos/1", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["preference_id"] == "pref-test-123"
    assert data["status"] == "pending"
    assert Decimal(str(data["monto_total"])) == Decimal("100000")


def test_get_pagos_admin(client, admin_headers, user_headers, mock_mp_sdk):
    _, preference_api, _ = mock_mp_sdk
    preference_api.create.return_value = MOCK_PREFERENCE_RESPONSE

    client.post(
        "/pagos/preferencia",
        headers=user_headers,
        json=PREFERENCIA_BODY,
    )

    response = client.get("/pagos/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["preference_id"] == "pref-test-123"
    assert data[0]["username"] == "regular_user"
