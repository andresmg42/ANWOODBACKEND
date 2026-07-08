from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from ..auth import get_current_active_user, require_permission
from ..database import SessionDep
from ..models import Cart, ItemCart, WoodPiece, User  
from ..schemas import DetailResponse, ItemCartAdd, ItemCartUpdate, CartPublic

router = APIRouter(prefix="/cart", tags=["cart"])


def _get_or_create_carrito(user: User, db) -> Cart:  
    carrito = db.exec(select(Cart).where(Cart.user_id == user.id)).first()  
    if not carrito:
        carrito = Cart(user_id=user.id) 
        db.add(carrito)
        db.commit()
        db.refresh(carrito)
    return carrito


def _get_carrito_item(item_id: int, carrito_id: int, db) -> ItemCart:  
    item = db.get(ItemCart, item_id)
    if not item or item.carrito_id != carrito_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en el carrito"
        )
    return item


@router.get("", response_model=CartPublic, summary="Ver carrito del usuario")
async def ver_carrito(
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    return carrito


@router.post(
    "/items",
    response_model=CartPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar pieza al carrito",
)
async def agregar_item(
    data: ItemCartAdd,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    pieza = db.get(WoodPiece, data.wood_piece_id)
    if not pieza:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pieza no encontrada")

    if pieza.estado != "disponible":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"La pieza {data.wood_piece_id} no está disponible")

    if data.cantidad <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad debe ser mayor a 0")

    carrito = _get_or_create_carrito(current_user, db)

    existing = db.exec(
        select(ItemCart)
        .where(ItemCart.carrito_id == carrito.id)
        .where(ItemCart.wood_piece_id == data.wood_piece_id)
    ).first()

    if existing:
        nueva_cantidad = existing.cantidad + data.cantidad
        if pieza.stock < data.cantidad: 
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Stock insuficiente. Solo hay {pieza.stock} unidades disponibles"
            )
        existing.cantidad = nueva_cantidad
    else:
        if pieza.stock < data.cantidad:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Stock insuficiente. Solo hay {pieza.stock} unidades disponibles"
            )
        item = ItemCart(carrito_id=carrito.id, wood_piece_id=data.wood_piece_id, cantidad=data.cantidad)
        db.add(item)

    pieza.cantidad_reservada += data.cantidad

    carrito.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(carrito)
    return carrito


@router.patch("/items/{item_id}", response_model=CartPublic, summary="Actualizar cantidad")
async def actualizar_item(
    item_id: int,
    data: ItemCartUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)

    if data.cantidad < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad no puede ser negativa")

    item = _get_carrito_item(item_id, carrito.id, db)
    pieza = db.get(WoodPiece, item.wood_piece_id)
    if not pieza:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pieza no encontrada")

    diferencia = data.cantidad - item.cantidad  

    if data.cantidad == 0:
        pieza.cantidad_reservada -= item.cantidad
        db.delete(item)
        carrito.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(carrito)
        return carrito

    if diferencia > 0 and pieza.stock < diferencia:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Stock insuficiente. Solo hay {pieza.stock} unidades disponibles"
        )

    pieza.cantidad_reservada += diferencia
    item.cantidad = data.cantidad
    carrito.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(carrito)
    return carrito


@router.delete("/items/{item_id}", response_model=DetailResponse, summary="Quitar item")
async def eliminar_item(
    item_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    item = _get_carrito_item(item_id, carrito.id, db)
    pieza = db.get(WoodPiece, item.wood_piece_id)

    if pieza:
        pieza.cantidad_reservada -= item.cantidad  

    db.delete(item)
    carrito.updated_at = datetime.utcnow()
    db.commit()
    return {"detail": "Item eliminado del carrito"}


@router.delete("", response_model=DetailResponse, summary="Vaciar carrito")
async def vaciar_carrito(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)

    for item in carrito.items[:]:
        pieza = db.get(WoodPiece, item.wood_piece_id)
        if pieza:
            pieza.cantidad_reservada -= item.cantidad  
        db.delete(item)

    carrito.updated_at = datetime.utcnow()
    db.commit()
    return {"detail": "Carrito vaciado"}