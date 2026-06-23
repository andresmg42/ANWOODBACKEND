from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ...models import ItemCart, TipoMadera, WoodPiece
from ._base import ExecutorBase
from ._helpers import decimal_to_float, pieza_disponible


class CartHandler(ExecutorBase):
    def consultar_carrito(self) -> dict[str, Any]:
        if err := self._require_auth():
            return err

        cart = self._get_or_create_cart()
        items = self.db.exec(
            select(ItemCart)
            .where(ItemCart.carrito_id == cart.id)
            .options(selectinload(ItemCart.pieza).selectinload(WoodPiece.tipo_madera))
        ).all()

        serializados = []
        subtotal = Decimal("0")
        for item in items:
            pieza = item.pieza or self.db.get(WoodPiece, item.wood_piece_id)
            if not pieza:
                continue
            precio = Decimal(str(pieza.precio_unitario or 0))
            qty = int(item.cantidad or 0)
            subtotal += precio * qty
            serializados.append(
                {
                    "item_id": item.id,
                    "pieza_id": pieza.id,
                    "tipo_madera": pieza.tipo_madera.nombre
                    if pieza.tipo_madera
                    else None,
                    "cantidad": qty,
                    "precio_unitario": decimal_to_float(pieza.precio_unitario),
                    "subtotal_item": float(precio * qty),
                }
            )

        return {
            "total_items": len(serializados),
            "subtotal_estimado": float(subtotal),
            "items": serializados,
        }

    def agregar_al_carrito(
        self,
        pieza_id: int | None = None,
        nombre_madera: str | None = None,
        cantidad: int = 1,
    ) -> dict[str, Any]:
        if err := self._require_auth():
            return err
        if cantidad <= 0:
            return {"error": "La cantidad debe ser mayor a 0."}

        pieza: WoodPiece | None = None
        if pieza_id is not None:
            pieza = self.db.get(WoodPiece, pieza_id)
        elif nombre_madera and nombre_madera.strip():
            term = nombre_madera.strip().lower()
            pieza = self.db.exec(
                select(WoodPiece)
                .join(TipoMadera)
                .where(
                    WoodPiece.estado == "disponible",
                    func.lower(TipoMadera.nombre).contains(term),
                )
                .options(selectinload(WoodPiece.tipo_madera))
            ).first()
        else:
            return {"error": "Indica pieza_id o nombre_madera."}

        if not pieza:
            return {"error": "Pieza no encontrada."}
        if pieza.estado != "disponible":
            return {"error": "La pieza no está disponible."}
        if pieza_disponible(pieza) < cantidad:
            return {
                "error": f"Stock insuficiente. Solo hay {pieza_disponible(pieza)} unidades.",
            }

        cart = self._get_or_create_cart()
        existing = self.db.exec(
            select(ItemCart)
            .where(ItemCart.carrito_id == cart.id)
            .where(ItemCart.wood_piece_id == pieza.id)
        ).first()

        if existing:
            existing.cantidad = (existing.cantidad or 0) + cantidad
        else:
            self.db.add(
                ItemCart(
                    carrito_id=cart.id,
                    wood_piece_id=pieza.id,
                    cantidad=cantidad,
                )
            )

        pieza.cantidad_reservada = (pieza.cantidad_reservada or 0) + cantidad
        cart.updated_at = datetime.utcnow()
        self.db.commit()

        return {
            "mensaje": "Producto agregado al carrito.",
            "pieza_id": pieza.id,
            "tipo_madera": pieza.tipo_madera.nombre if pieza.tipo_madera else None,
            "cantidad_agregada": cantidad,
        }

    def eliminar_del_carrito(self, item_id: int) -> dict[str, Any]:
        if err := self._require_auth():
            return err

        cart = self._get_or_create_cart()
        item = self.db.get(ItemCart, item_id)
        if not item or item.carrito_id != cart.id:
            return {"error": "Item no encontrado en tu carrito."}

        pieza = self.db.get(WoodPiece, item.wood_piece_id)
        if pieza:
            pieza.cantidad_reservada = max(
                0, (pieza.cantidad_reservada or 0) - (item.cantidad or 0)
            )

        self.db.delete(item)
        cart.updated_at = datetime.utcnow()
        self.db.commit()
        return {"mensaje": "Item eliminado del carrito.", "item_id": item_id}

    def vaciar_carrito(self) -> dict[str, Any]:
        if err := self._require_auth():
            return err

        cart = self._get_or_create_cart()
        items = self.db.exec(
            select(ItemCart).where(ItemCart.carrito_id == cart.id)
        ).all()
        for item in items:
            pieza = self.db.get(WoodPiece, item.wood_piece_id)
            if pieza:
                pieza.cantidad_reservada = max(
                    0, (pieza.cantidad_reservada or 0) - (item.cantidad or 0)
                )
            self.db.delete(item)

        cart.updated_at = datetime.utcnow()
        self.db.commit()
        return {"mensaje": "Carrito vaciado.", "items_eliminados": len(items)}
