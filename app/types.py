from decimal import Decimal
from typing import Annotated, Any

from pydantic import PlainSerializer, WithJsonSchema

DECIMAL_JSON_SCHEMA = {
    "type": "string",
    "format": "decimal",
    "examples": ["3.5"],
    "description": "Número decimal serializado como string.",
}


def normalize_decimal(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


ApiDecimal = Annotated[
    Decimal,
    PlainSerializer(normalize_decimal, return_type=str, when_used="json"),
    WithJsonSchema(DECIMAL_JSON_SCHEMA),
]
