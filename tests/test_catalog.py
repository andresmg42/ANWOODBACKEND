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


def test_create_categoria_requires_permission(client, user_headers):
    response = client.post(
        "/categorias/",
        headers=user_headers,
        json={
            "nombre": "Nueva Categoria",
            "estrategia_precio": "por_volumen",
            "permite_cubicacion": True,
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
            "permite_cubicacion": True,
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
