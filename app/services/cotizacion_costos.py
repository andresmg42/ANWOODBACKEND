from decimal import Decimal

from sqlmodel import Session

from ..models import ViaTransporteEnum
from .config_service import get_decimal_config

ZERO = Decimal("0")

VIAS = (ViaTransporteEnum.TIERRA.value, ViaTransporteEnum.MAR.value)

_CONFIG_KEYS_BY_VIA = {
    ViaTransporteEnum.TIERRA.value: {
        "transporte": "costo_transporte_tierra_defecto",
        "cargue": "costo_cargue_tierra_defecto",
        "descargue": "costo_descargue_tierra_defecto",
        "tasa_salvoconducto": "tasa_salvoconducto_tierra_por_m3",
    },
    ViaTransporteEnum.MAR.value: {
        "transporte": "costo_transporte_mar_defecto",
        "cargue": "costo_cargue_mar_defecto",
        "descargue": "costo_descargue_mar_defecto",
        "tasa_salvoconducto": "tasa_salvoconducto_mar_por_m3",
    },
}

_LEGACY_CONFIG_KEYS = {
    "transporte": "costo_transporte_defecto",
    "cargue": "costo_cargue_defecto",
    "descargue": "costo_descargue_defecto",
    "tasa_salvoconducto": "tasa_salvoconducto_por_m3",
}


def normalizar_via_transporte(via: str | None) -> str:
    if via is None:
        return ViaTransporteEnum.TIERRA.value
    via_normalizada = via.strip().lower()
    if via_normalizada not in VIAS:
        raise ValueError(
            f"Vía de transporte inválida: {via!r}. Use 'tierra' o 'mar'."
        )
    return via_normalizada


def _get_config_por_via(
    db: Session, via: str, concepto: str, default: Decimal = ZERO
) -> Decimal:
    clave = _CONFIG_KEYS_BY_VIA[via][concepto]
    legacy = get_decimal_config(db, _LEGACY_CONFIG_KEYS[concepto], default)
    return get_decimal_config(db, clave, legacy)


def get_costos_defecto_por_via(db: Session, via_transporte: str) -> dict[str, Decimal]:
    via = normalizar_via_transporte(via_transporte)
    return {
        "costo_transporte": _get_config_por_via(db, via, "transporte"),
        "costo_cargue": _get_config_por_via(db, via, "cargue"),
        "costo_descargue": _get_config_por_via(db, via, "descargue"),
    }


def calcular_salvoconducto(
    db: Session, total_m3: Decimal, via_transporte: str
) -> Decimal:
    via = normalizar_via_transporte(via_transporte)
    tasa = _get_config_por_via(db, via, "tasa_salvoconducto")
    return total_m3 * tasa
