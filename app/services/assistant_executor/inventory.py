from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ...models import TipoMadera, WoodPiece
from ._base import ExecutorBase
from ._helpers import serialize_pieza


class InventoryHandler(ExecutorBase):
    def consultar_inventario(
        self,
        nombre_madera: str | None = None,
        tipo_madera_id: int | None = None,
        solo_con_stock: bool = True,
    ) -> dict[str, Any]:
        query = (
            select(WoodPiece)
            .where(WoodPiece.estado == "disponible")
            .options(
                selectinload(WoodPiece.tipo_madera),
                selectinload(WoodPiece.medida),
            )
        )
        if tipo_madera_id is not None:
            query = query.where(WoodPiece.tipo_madera_id == tipo_madera_id)
        elif nombre_madera and nombre_madera.strip():
            term = nombre_madera.strip().lower()
            tipo_ids = self.db.exec(
                select(TipoMadera.id).where(
                    func.lower(TipoMadera.nombre).contains(term)
                )
            ).all()
            if not tipo_ids:
                return {"total": 0, "piezas": [], "mensaje": "No se encontró ese tipo."}
            query = query.where(WoodPiece.tipo_madera_id.in_(tipo_ids))

        piezas = self.db.exec(query.limit(50)).unique().all()
        serializadas = []
        for pieza in piezas:
            data = serialize_pieza(pieza)
            if solo_con_stock and data["cantidad_disponible"] <= 0:
                continue
            serializadas.append(data)

        resumen_stock = sum(p["cantidad_disponible"] for p in serializadas)
        return {
            "total_piezas": len(serializadas),
            "unidades_disponibles": resumen_stock,
            "piezas": serializadas,
        }
