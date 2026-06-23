from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ...models import Categoria, Medida, TipoMadera
from ._base import ExecutorBase
from ._helpers import decimal_to_float, serialize_tipo_madera, stock_disponible


class CatalogHandler(ExecutorBase):
    def consultar_catalogo(
        self,
        nombre_madera: str | None = None,
        categoria: str | None = None,
    ) -> dict[str, Any]:
        query = (
            select(TipoMadera)
            .where(TipoMadera.activo == True)  # noqa: E712
            .options(selectinload(TipoMadera.categoria))
        )
        if nombre_madera and nombre_madera.strip():
            term = nombre_madera.strip().lower()
            query = query.where(func.lower(TipoMadera.nombre).contains(term))
        if categoria and categoria.strip():
            term = categoria.strip().lower()
            query = query.join(Categoria).where(
                func.lower(Categoria.nombre).contains(term)
            )

        tipos = self.db.exec(query).all()
        resultados = [
            serialize_tipo_madera(tipo, stock_disponible(self.db, tipo.id))
            for tipo in tipos
        ]
        return {"total": len(resultados), "tipos_madera": resultados}

    def consultar_medidas(self) -> dict[str, Any]:
        medidas = self.db.exec(
            select(Medida).where(Medida.es_estandar == True)  # noqa: E712
        ).all()
        return {
            "total": len(medidas),
            "medidas": [
                {
                    "id": m.id,
                    "etiqueta": m.etiqueta,
                    "ancho_in": decimal_to_float(m.ancho_in),
                    "alto_in": decimal_to_float(m.alto_in),
                }
                for m in medidas
            ],
        }
