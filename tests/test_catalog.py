from decimal import Decimal


def test_list_categorias_from_seed(client):
    response = client.get("/categorias/")

    assert response.status_code == 200
    nombres = {categoria["nombre"] for categoria in response.json()}
    assert "Madera Corta" in nombres
    assert "Madera Larga" in nombres


def test_list_wood_types_from_seed(client):
    response = client.get("/wood-types/")

    assert response.status_code == 200
    nombres = {tipo["nombre"] for tipo in response.json()}
    assert "Chaquiro" in nombres
    assert "Popa" in nombres


def test_list_medidas_from_seed(client):
    response = client.get("/medidas/")

    assert response.status_code == 200
    etiquetas = {medida["etiqueta"] for medida in response.json()}
    assert "2x5" in etiquetas
    assert "3x6" in etiquetas
    assert all("cubica" in medida for medida in response.json())
    assert all("permite_cubicacion" not in medida for medida in response.json())


def test_create_categoria_requires_permission(client, user_headers):
    response = client.post(
        "/categorias/",
        headers=user_headers,
        json={
            "nombre": "Nueva Categoria",
            "estrategia_precio": "por_volumen",
            "formula_cubicacion": "largo_x_alto_x_ancho_div_10",
        },
    )

    assert response.status_code == 403


def test_create_categoria_as_admin(client, admin_headers):
    response = client.post(
        "/categorias/",
        headers=admin_headers,
        json={
            "nombre": "Tableros",
            "estrategia_precio": "por_volumen",
            "formula_cubicacion": "largo_x_alto_x_ancho_div_10",
            "min_precio_m3": "1500",
        },
    )

    assert response.status_code == 201
    assert response.json()["nombre"] == "Tableros"


def test_list_piezas_from_seed(client):
    response = client.get("/piezas")

    assert response.status_code == 200
    piezas = response.json()
    assert len(piezas) >= 2
    assert all("cantidad" in pieza for pieza in piezas)
    assert all("ancho_in" in pieza for pieza in piezas)
    assert all("alto_in" in pieza for pieza in piezas)
    assert all("calidad" in pieza for pieza in piezas)
    assert all("created_at" in pieza for pieza in piezas)
    assert all("fecha_ingreso" not in pieza for pieza in piezas)


def test_create_pieza_uses_medida_dimensions_by_default(client, admin_headers):
    medidas_response = client.get("/medidas/")
    medida = next(m for m in medidas_response.json() if m["etiqueta"] == "3x6")
    tipos_response = client.get("/wood-types/")
    tipo = next(t for t in tipos_response.json() if t["nombre"] == "Chaquiro")
    lotes_response = client.get("/lotes", headers=admin_headers)
    lote_id = lotes_response.json()[0]["id"]

    response = client.post(
        "/piezas",
        headers=admin_headers,
        json={
            "tipo_madera_id": tipo["id"],
            "medida_id": medida["id"],
            "lote_id": lote_id,
            "largo_m": "4",
            "cantidad": 5,
            "costo_unitario": "1000",
            "precio_unitario": "1500",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["ancho_in"]) == Decimal(medida["ancho_in"])
    assert Decimal(data["alto_in"]) == Decimal(medida["alto_in"])


def test_create_pieza_with_custom_dimensions(client, admin_headers):
    medidas_response = client.get("/medidas/")
    medida = next(m for m in medidas_response.json() if m["etiqueta"] == "3x6")
    tipos_response = client.get("/wood-types/")
    tipo = next(t for t in tipos_response.json() if t["nombre"] == "Chaquiro")
    lotes_response = client.get("/lotes", headers=admin_headers)
    lote_id = lotes_response.json()[0]["id"]

    response = client.post(
        "/piezas",
        headers=admin_headers,
        json={
            "tipo_madera_id": tipo["id"],
            "medida_id": medida["id"],
            "lote_id": lote_id,
            "ancho_in": "4",
            "alto_in": "7",
            "largo_m": "4",
            "cantidad": 2,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert Decimal(data["ancho_in"]) == Decimal("4")
    assert Decimal(data["alto_in"]) == Decimal("7")


def test_list_lotes_includes_fecha_ingreso(client, admin_headers):
    response = client.get("/lotes", headers=admin_headers)

    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert "fecha_ingreso" in response.json()[0]


def test_create_pieza_with_calidad(client, admin_headers):
    medidas_response = client.get("/medidas/")
    medida = next(m for m in medidas_response.json() if m["etiqueta"] == "3x6")
    tipos_response = client.get("/wood-types/")
    tipo = next(t for t in tipos_response.json() if t["nombre"] == "Chaquiro")
    lotes_response = client.get("/lotes", headers=admin_headers)
    lote_id = lotes_response.json()[0]["id"]

    response = client.post(
        "/piezas",
        headers=admin_headers,
        json={
            "tipo_madera_id": tipo["id"],
            "medida_id": medida["id"],
            "lote_id": lote_id,
            "largo_m": "4",
            "cantidad": 1,
            "calidad": "primera",
        },
    )

    assert response.status_code == 201
    assert response.json()["calidad"] == "primera"
