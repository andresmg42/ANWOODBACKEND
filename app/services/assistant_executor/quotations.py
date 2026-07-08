from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlmodel import select

from ...models import Cart, Cotizacion, DetalleCotizacion, ItemCart, WoodPiece
from ..cotizacion_costos import (
    calcular_salvoconducto,
    get_costos_defecto_por_via,
    normalizar_via_transporte,
)
from ._base import ExecutorBase
from ._helpers import decimal_to_float, get_config_decimal, get_config_int


class QuotationHandler(ExecutorBase):
    def consultar_cotizaciones(
        self,
        numero_cotizacion: str | None = None,
        cotizacion_id: int | None = None,
    ) -> dict[str, Any]:
        if err := self._require_auth():
            return err

        query = select(Cotizacion).where(Cotizacion.user_id == self.user_id)
        if cotizacion_id is not None:
            query = query.where(Cotizacion.id == cotizacion_id)
        elif numero_cotizacion:
            query = query.where(
                Cotizacion.numero_cotizacion.contains(numero_cotizacion.strip())
            )

        cotizaciones = self.db.exec(query.order_by(Cotizacion.created_at.desc())).all()
        return {
            "total": len(cotizaciones),
            "cotizaciones": [
                {
                    "id": c.id,
                    "numero_cotizacion": c.numero_cotizacion,
                    "estado": c.estado,
                    "via_transporte": c.via_transporte,
                    "total_m3": decimal_to_float(c.total_m3),
                    "subtotal": decimal_to_float(c.subtotal),
                    "total_monto": decimal_to_float(c.total_monto),
                    "valor_anticipo": decimal_to_float(c.valor_anticipo),
                    "fecha_emision": c.fecha_emision.isoformat()
                    if c.fecha_emision
                    else None,
                    "fecha_vencimiento": c.fecha_vencimiento.isoformat()
                    if c.fecha_vencimiento
                    else None,
                }
                for c in cotizaciones
            ],
        }

    def generar_cotizacion(self, via_transporte: str | None = None) -> dict[str, Any]:
        if err := self._require_auth():
            return err

        try:
            via = normalizar_via_transporte(via_transporte)
        except ValueError as exc:
            return {"error": str(exc)}

        cart = self.db.exec(select(Cart).where(Cart.user_id == self.user_id)).first()
        if not cart:
            return {"error": "No tienes carrito. Agrega productos primero."}

        items = self.db.exec(
            select(ItemCart).where(ItemCart.carrito_id == cart.id)
        ).all()
        if not items:
            return {"error": "Tu carrito está vacío. Agrega piezas antes de cotizar."}

        total_m3 = Decimal("0")
        subtotal = Decimal("0")
        for item in items:
            pieza = self.db.get(WoodPiece, item.wood_piece_id)
            if not pieza or pieza.volumen_m3 is None or pieza.precio_unitario is None:
                return {"error": f"La pieza {item.wood_piece_id} no tiene datos completos."}
            qty = Decimal(str(item.cantidad or 0))
            total_m3 += Decimal(str(pieza.volumen_m3)) * qty
            subtotal += Decimal(str(pieza.precio_unitario)) * qty

        porcentaje = get_config_decimal(self.db, "porcentaje_anticipo")
        dias_vencimiento = get_config_int(self.db, "dias_vencimiento_cotizacion", 10)
        costos_defecto = get_costos_defecto_por_via(self.db, via)
        costo_transporte = costos_defecto["costo_transporte"]
        costo_cargue = costos_defecto["costo_cargue"]
        costo_descargue = costos_defecto["costo_descargue"]
        costo_salvoconducto = calcular_salvoconducto(self.db, total_m3, via)
        valor_anticipo = subtotal * (porcentaje / Decimal("100"))
        total_monto = (
            subtotal + costo_transporte + costo_cargue + costo_descargue + costo_salvoconducto
        )

        fecha_emision = datetime.utcnow()
        numero = f"COT-{fecha_emision.year}-{uuid4()}"
        cotizacion = Cotizacion(
            user_id=self.user_id,
            numero_cotizacion=numero,
            estado="pendiente",
            via_transporte=via,
            total_m3=total_m3,
            subtotal=subtotal,
            costo_transporte=costo_transporte,
            costo_cargue=costo_cargue,
            costo_descargue=costo_descargue,
            costo_salvoconducto=costo_salvoconducto,
            porcentaje_anticipo=porcentaje,
            valor_anticipo=valor_anticipo,
            total_monto=total_monto,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_emision + timedelta(days=dias_vencimiento),
        )
        self.db.add(cotizacion)
        self.db.flush()

        for item in items:
            pieza = self.db.get(WoodPiece, item.wood_piece_id)
            if not pieza:
                continue
            qty = int(item.cantidad or 0)
            precio = Decimal(str(pieza.precio_unitario))
            self.db.add(
                DetalleCotizacion(
                    cotizacion_id=cotizacion.id,
                    pieza_id=pieza.id,
                    descripcion_item=f"Pieza {pieza.id}",
                    cantidad=qty,
                    volumen_unitario_m3=Decimal(str(pieza.volumen_m3)),
                    precio_unitario_snapshot=precio,
                    subtotal=precio * Decimal(str(qty)),
                )
            )

        self.db.commit()
        self.db.refresh(cotizacion)
        return {
            "mensaje": "Cotización generada exitosamente.",
            "cotizacion": {
                "id": cotizacion.id,
                "numero_cotizacion": cotizacion.numero_cotizacion,
                "estado": cotizacion.estado,
                "via_transporte": cotizacion.via_transporte,
                "total_monto": decimal_to_float(cotizacion.total_monto),
                "valor_anticipo": decimal_to_float(cotizacion.valor_anticipo),
                "fecha_vencimiento": cotizacion.fecha_vencimiento.isoformat()
                if cotizacion.fecha_vencimiento
                else None,
            },
        }
