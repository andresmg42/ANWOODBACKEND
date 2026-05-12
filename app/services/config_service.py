from decimal import Decimal, InvalidOperation

from sqlmodel import select

from ..models import Configuration


def get_decimal_config(db, key: str, default: Decimal) -> Decimal:
    config = db.exec(select(Configuration).where(Configuration.clave == key)).first()
    if not config or config.valor is None:
        return default

    try:
        return Decimal(str(config.valor))
    except (InvalidOperation, ValueError, TypeError):
        return default
