from typing import Any

from sqlmodel import Session

from .cart import CartHandler
from .catalog import CatalogHandler
from .company import CompanyHandler
from .inventory import InventoryHandler
from .quotations import QuotationHandler
from .recommendations import RecommendationHandler

HANDLERS: dict[str, str] = {
    "informacion_empresa": "informacion_empresa",
    "consultar_catalogo": "consultar_catalogo",
    "consultar_medidas": "consultar_medidas",
    "consultar_inventario": "consultar_inventario",
    "consultar_piezas": "consultar_inventario",
    "consultar_cotizaciones": "consultar_cotizaciones",
    "generar_cotizacion": "generar_cotizacion",
    "consultar_carrito": "consultar_carrito",
    "agregar_al_carrito": "agregar_al_carrito",
    "eliminar_del_carrito": "eliminar_del_carrito",
    "vaciar_carrito": "vaciar_carrito",
    "recomendar_productos": "recomendar_productos",
}


class AssistantExecutor(
    CompanyHandler,
    CatalogHandler,
    InventoryHandler,
    QuotationHandler,
    CartHandler,
    RecommendationHandler,
):

    def __init__(self, db: Session, user_id: int | None = None):
        super().__init__(db, user_id)

    def execute(self, function_name: str, args: dict[str, Any]) -> dict[str, Any]:
        method_name = HANDLERS.get(function_name)
        if method_name is None:
            return {"error": f"Función desconocida: {function_name}"}
        handler = getattr(self, method_name)
        return handler(**args)


__all__ = ["AssistantExecutor"]
