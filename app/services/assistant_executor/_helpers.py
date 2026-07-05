from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from ...models import Configuration, TipoMadera, WoodPiece


def decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def auth_error() -> dict[str, Any]:
    return {
        "error": "Esta operación requiere iniciar sesión.",
        "requiere_autenticacion": True,
    }


def stock_disponible(db: Session, tipo_madera_id: int) -> int:
    piezas = db.exec(
        select(WoodPiece).where(
            WoodPiece.tipo_madera_id == tipo_madera_id,
            WoodPiece.estado == "disponible",
        )
    ).all()
    return sum(max(0, (p.cantidad or 0) - (p.cantidad_reservada or 0)) for p in piezas)


def pieza_disponible(pieza: WoodPiece) -> int:
    return max(0, (pieza.cantidad or 0) - (pieza.cantidad_reservada or 0))


def serialize_tipo_madera(tipo: TipoMadera, stock: int) -> dict[str, Any]:
    return {
        "id": tipo.id,
        "nombre": tipo.nombre,
        "precio_por_metro": decimal_to_float(tipo.precio_por_metro),
        "activo": tipo.activo,
        "descripcion": tipo.descripcion,
        "categoria": tipo.categoria.nombre if tipo.categoria else None,
        "stock_disponible": stock,
    }


def serialize_pieza(pieza: WoodPiece) -> dict[str, Any]:
    disponible = pieza_disponible(pieza)
    medida = pieza.medida
    return {
        "id": pieza.id,
        "tipo_madera": pieza.tipo_madera.nombre if pieza.tipo_madera else None,
        "medida": medida.etiqueta if medida else None,
        "largo_m": decimal_to_float(pieza.largo_m),
        "volumen_m3": decimal_to_float(pieza.volumen_m3),
        "cantidad_disponible": disponible,
        "precio_unitario": decimal_to_float(pieza.precio_unitario),
    }


def get_config_decimal(db: Session, key: str, default: Decimal = Decimal("0")) -> Decimal:
    config = db.exec(select(Configuration).where(Configuration.clave == key)).first()
    if not config or config.valor is None:
        return default
    return Decimal(str(config.valor))


def get_config_int(db: Session, key: str, default: int = 0) -> int:
    return int(get_config_decimal(db, key, Decimal(str(default))))


