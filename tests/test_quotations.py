from decimal import Decimal

from sqlmodel import select

from app.models import Configuration, User
from app.services.assistant_executor import AssistantExecutor
from tests.conftest import TEST_USER_USERNAME


def _set_config(session, clave: str, valor: str) -> None:
    config = session.exec(
        select(Configuration).where(Configuration.clave == clave)
    ).one()
    config.valor = valor
    session.add(config)
    session.commit()


def _regular_user_id(client, admin_headers) -> int:
    users = client.get("/users", headers=admin_headers).json()
    return next(user["id"] for user in users if user["username"] == TEST_USER_USERNAME)


def _add_pieza_con_volumen_al_carrito(client, user_headers) -> dict:
    piezas = client.get("/piezas").json()
    pieza = next(
        item for item in piezas if item.get("volumen_m3") and float(item["volumen_m3"]) > 0
    )
    response = client.post(
        "/cart/items",
        headers=user_headers,
        json={"wood_piece_id": pieza["id"], "cantidad": 2},
    )
    assert response.status_code == 201
    return pieza


def _crear_cotizacion(client, user_id: int, via_transporte: str | None = None) -> dict:
    payload = {"user_id": user_id}
    if via_transporte is not None:
        payload["via_transporte"] = via_transporte
    response = client.post("/cotizaciones", json=payload)
    assert response.status_code == 201
    return response.json()


def _totales_esperados(
    subtotal: Decimal,
    total_m3: Decimal,
    transporte: Decimal,
    cargue: Decimal,
    descargue: Decimal,
    tasa_salvoconducto: Decimal,
) -> dict[str, Decimal]:
    costo_salvoconducto = total_m3 * tasa_salvoconducto
    total_monto = subtotal + transporte + cargue + descargue + costo_salvoconducto
    valor_anticipo = subtotal * Decimal("0.2")
    return {
        "costo_salvoconducto": costo_salvoconducto,
        "total_monto": total_monto,
        "valor_anticipo": valor_anticipo,
    }


def test_create_cotizacion_via_tierra_uses_tierra_defaults(
    client, user_headers, admin_headers, session
):
    pieza = _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)

    data = _crear_cotizacion(client, user_id, via_transporte="tierra")

    subtotal = Decimal(str(pieza["precio_unitario"])) * 2
    total_m3 = Decimal(str(pieza["volumen_m3"])) * 2
    esperado = _totales_esperados(
        subtotal=subtotal,
        total_m3=total_m3,
        transporte=Decimal("500000"),
        cargue=Decimal("200000"),
        descargue=Decimal("200000"),
        tasa_salvoconducto=Decimal("10"),
    )

    assert data["via_transporte"] == "tierra"
    assert Decimal(str(data["subtotal"])) == subtotal
    assert Decimal(str(data["costo_transporte"])) == Decimal("500000")
    assert Decimal(str(data["costo_cargue"])) == Decimal("200000")
    assert Decimal(str(data["costo_descargue"])) == Decimal("200000")
    assert Decimal(str(data["costo_salvoconducto"])) == esperado["costo_salvoconducto"]
    assert Decimal(str(data["total_monto"])) == esperado["total_monto"]
    assert Decimal(str(data["valor_anticipo"])) == esperado["valor_anticipo"]


def test_create_cotizacion_via_mar_uses_mar_defaults(
    client, user_headers, admin_headers, session
):
    _set_config(session, "costo_transporte_mar_defecto", "600000")
    _set_config(session, "costo_cargue_mar_defecto", "250000")
    _set_config(session, "costo_descargue_mar_defecto", "180000")
    _set_config(session, "tasa_salvoconducto_mar_por_m3", "15")

    pieza = _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)

    data = _crear_cotizacion(client, user_id, via_transporte="mar")

    subtotal = Decimal(str(pieza["precio_unitario"])) * 2
    total_m3 = Decimal(str(pieza["volumen_m3"])) * 2
    esperado = _totales_esperados(
        subtotal=subtotal,
        total_m3=total_m3,
        transporte=Decimal("600000"),
        cargue=Decimal("250000"),
        descargue=Decimal("180000"),
        tasa_salvoconducto=Decimal("15"),
    )

    assert data["via_transporte"] == "mar"
    assert Decimal(str(data["costo_transporte"])) == Decimal("600000")
    assert Decimal(str(data["costo_cargue"])) == Decimal("250000")
    assert Decimal(str(data["costo_descargue"])) == Decimal("180000")
    assert Decimal(str(data["costo_salvoconducto"])) == esperado["costo_salvoconducto"]
    assert Decimal(str(data["total_monto"])) == esperado["total_monto"]


def test_create_cotizacion_default_via_is_tierra(client, user_headers, admin_headers):
    _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)

    data = _crear_cotizacion(client, user_id)

    assert data["via_transporte"] == "tierra"
    assert Decimal(str(data["costo_transporte"])) == Decimal("500000")


def test_create_cotizacion_invalid_via_returns_400(client, user_headers, admin_headers):
    _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)

    response = client.post(
        "/cotizaciones",
        json={"user_id": user_id, "via_transporte": "aereo"},
    )

    assert response.status_code == 400
    assert "tierra" in response.json()["detail"]


def test_patch_via_transporte_without_recalculating_costs(
    client, user_headers, admin_headers, session
):
    _set_config(session, "costo_transporte_mar_defecto", "600000")

    pieza = _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)
    cotizacion = _crear_cotizacion(client, user_id, via_transporte="tierra")
    costo_transporte_original = cotizacion["costo_transporte"]

    response = client.patch(
        f"/cotizaciones/{cotizacion['id']}",
        json={"via_transporte": "mar"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["via_transporte"] == "mar"
    assert data["costo_transporte"] == costo_transporte_original
    assert Decimal(str(data["subtotal"])) == Decimal(str(pieza["precio_unitario"])) * 2


def test_recalcular_cotizacion_uses_via_transporte(
    client, user_headers, admin_headers, session
):
    _set_config(session, "costo_transporte_mar_defecto", "600000")
    _set_config(session, "costo_cargue_mar_defecto", "250000")
    _set_config(session, "costo_descargue_mar_defecto", "180000")
    _set_config(session, "tasa_salvoconducto_mar_por_m3", "15")

    pieza = _add_pieza_con_volumen_al_carrito(client, user_headers)
    user_id = _regular_user_id(client, admin_headers)
    cotizacion = _crear_cotizacion(client, user_id, via_transporte="tierra")

    client.patch(
        f"/cotizaciones/{cotizacion['id']}",
        json={"via_transporte": "mar"},
    )

    response = client.patch(
        f"/cotizaciones/{cotizacion['id']}",
        json={"recalcular": True},
    )

    assert response.status_code == 200
    data = response.json()

    subtotal = Decimal(str(pieza["precio_unitario"])) * 2
    total_m3 = Decimal(str(pieza["volumen_m3"])) * 2
    esperado = _totales_esperados(
        subtotal=subtotal,
        total_m3=total_m3,
        transporte=Decimal("600000"),
        cargue=Decimal("250000"),
        descargue=Decimal("180000"),
        tasa_salvoconducto=Decimal("15"),
    )

    assert data["via_transporte"] == "mar"
    assert Decimal(str(data["costo_transporte"])) == Decimal("600000")
    assert Decimal(str(data["costo_cargue"])) == Decimal("250000")
    assert Decimal(str(data["costo_descargue"])) == Decimal("180000")
    assert Decimal(str(data["costo_salvoconducto"])) == esperado["costo_salvoconducto"]
    assert Decimal(str(data["total_monto"])) == esperado["total_monto"]


def test_assistant_generar_cotizacion_via_mar(session, client, user_headers, admin_headers):
    _set_config(session, "costo_transporte_mar_defecto", "600000")
    _set_config(session, "tasa_salvoconducto_mar_por_m3", "15")

    _add_pieza_con_volumen_al_carrito(client, user_headers)
    user = session.exec(
        select(User).where(User.username == TEST_USER_USERNAME)
    ).one()

    result = AssistantExecutor(session, user_id=user.id).generar_cotizacion(
        via_transporte="mar"
    )

    assert "error" not in result
    assert result["cotizacion"]["via_transporte"] == "mar"
    assert result["cotizacion"]["total_monto"] > 0
