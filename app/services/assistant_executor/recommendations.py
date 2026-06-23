from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ...models import Categoria, TipoMadera
from ._base import ExecutorBase
from ._helpers import serialize_tipo_madera, stock_disponible

PURPOSE_HINTS: dict[str, dict[str, Any]] = {
    "construccion": {"priorizar_stock": True},
    "estructura": {"priorizar_stock": True},
    "muebles": {"priorizar_stock": True},
    "exterior": {"nombres_sugeridos": ["Cedro", "Roble"]},
    "economico": {"ordenar_por": "precio_asc"},
}


class RecommendationHandler(ExecutorBase):
    def recomendar_productos(
        self,
        proposito: str | None = None,
        presupuesto_max_por_metro: float | None = None,
        categoria: str | None = None,
    ) -> dict[str, Any]:
        query = (
            select(TipoMadera)
            .where(TipoMadera.activo == True)  
            .options(selectinload(TipoMadera.categoria))
        )
        if categoria and categoria.strip():
            term = categoria.strip().lower()
            query = query.join(Categoria).where(
                func.lower(Categoria.nombre).contains(term)
            )

        tipos = self.db.exec(query).all()
        hints = PURPOSE_HINTS.get((proposito or "").strip().lower(), {})

        candidatos = []
        for tipo in tipos:
            stock = stock_disponible(self.db, tipo.id)
            precio = float(tipo.precio_por_metro)
            cat_nombre = tipo.categoria.nombre if tipo.categoria else None

            if presupuesto_max_por_metro is not None and precio > presupuesto_max_por_metro:
                continue

            hint_cats = hints.get("categorias", [])
            if hint_cats and cat_nombre and cat_nombre not in hint_cats:
                continue

            score = stock * 10
            nombres_sugeridos = hints.get("nombres_sugeridos", [])
            if tipo.nombre in nombres_sugeridos:
                score += 50
            if hints.get("priorizar_stock") and stock > 0:
                score += 30

            candidatos.append({**serialize_tipo_madera(tipo, stock), "puntuacion": score})

        if hints.get("ordenar_por") == "precio_asc":
            candidatos.sort(key=lambda x: x["precio_por_metro"] or 0)
        else:
            candidatos.sort(key=lambda x: x["puntuacion"], reverse=True)

        top = candidatos[:5]
        return {
            "proposito": proposito,
            "total_recomendaciones": len(top),
            "recomendaciones": top,
            "nota_asesoria": (
                "Las recomendaciones consideran stock disponible, categoría y propósito. "
                "Para proyectos estructurales se sugiere Madera Larga; "
                "para trabajos menores, Madera Corta."
            ),
        }
