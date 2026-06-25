from decimal import Decimal

import pytest
from sqlmodel import select

from app.models import Configuration
from app.services.cotizacion_costos import (
    calcular_salvoconducto,
    get_costos_defecto_por_via,
    normalizar_via_transporte,
)


def _set_config(session, clave: str, valor: str) -> None:
    config = session.exec(
        select(Configuration).where(Configuration.clave == clave)
    ).one()
    config.valor = valor
    session.add(config)
    session.commit()


def test_normalizar_via_transporte_defaults_to_tierra():
    assert normalizar_via_transporte(None) == "tierra"


def test_normalizar_via_transporte_accepts_mar_with_whitespace():
    assert normalizar_via_transporte("  MAR  ") == "mar"


def test_normalizar_via_transporte_rejects_invalid():
    with pytest.raises(ValueError, match="tierra' o 'mar"):
        normalizar_via_transporte("aereo")


def test_get_costos_defecto_por_via_tierra(session):
    costos = get_costos_defecto_por_via(session, "tierra")

    assert costos["costo_transporte"] == Decimal("500000")
    assert costos["costo_cargue"] == Decimal("200000")
    assert costos["costo_descargue"] == Decimal("200000")


def test_get_costos_defecto_por_via_mar(session):
    _set_config(session, "costo_transporte_mar_defecto", "600000")
    _set_config(session, "costo_cargue_mar_defecto", "250000")
    _set_config(session, "costo_descargue_mar_defecto", "180000")

    costos = get_costos_defecto_por_via(session, "mar")

    assert costos["costo_transporte"] == Decimal("600000")
    assert costos["costo_cargue"] == Decimal("250000")
    assert costos["costo_descargue"] == Decimal("180000")


def test_calcular_salvoconducto_uses_tasa_por_via(session):
    total_m3 = Decimal("14.4")

    salvoconducto_tierra = calcular_salvoconducto(session, total_m3, "tierra")
    assert salvoconducto_tierra == Decimal("144")

    _set_config(session, "tasa_salvoconducto_mar_por_m3", "15")
    salvoconducto_mar = calcular_salvoconducto(session, total_m3, "mar")
    assert salvoconducto_mar == Decimal("216")
