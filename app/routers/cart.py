from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from ..auth import get_current_active_user, require_permission
from ..database import SessionDep
from ..models import Cart, ItemCart, WoodPiece, User  
from ..schemas import ItemCartAdd, ItemCartUpdate, CartPublic

router = APIRouter(prefix="/cart", tags=["cart"])


def _get_or_create_carrito(user: User, db) -> Cart:  
    carrito = db.exec(select(Cart).where(Cart.usuario_id == user.id)).first()
    if not carrito:
        carrito = Cart(usuario_id=user.id)
        db.add(carrito)
        db.commit()
        db.refresh(carrito)
    return carrito


def _get_carrito_item(item_id: int, carrito_id: int, db) -> ItemCart:  
    """Helper para obtener un item del carrito con validación"""
    item = db.get(ItemCart, item_id)
    if not item or item.carrito_id != carrito_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item no encontrado en el carrito"
        )
    return item


@router.get("", response_model=CartPublic)
async def ver_carrito(
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    return carrito


@router.post("/items", response_model=CartPublic, status_code=status.HTTP_201_CREATED)
async def agregar_item(
    data: ItemCartAdd,
    current_user: Annotated[User, Depends(get_current_active_user)],  
    db: SessionDep,
):
    # Validar que la pieza existe y está disponible
    pieza = db.get(WoodPiece, data.pieza_id)  
    if not pieza:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pieza no encontrada")
    
    if not hasattr(pieza, 'estado') or pieza.estado != "disponible":
        pass

    # Validar cantidad positiva
    if data.cantidad <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La cantidad debe ser mayor a 0")

    carrito = _get_or_create_carrito(current_user, db)

    existing = db.exec(
        select(ItemCart)
        .where(ItemCart.carrito_id == carrito.id)
        .where(ItemCart.wood_piece_id == data.pieza_id)
    ).first()

    if existing:
        existing.cantidad += data.cantidad
    else:
        item = ItemCart(
            carrito_id=carrito.id,
            wood_piece_id=data.pieza_id,  
            cantidad=data.cantidad
        )
        db.add(item)

    carrito.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(carrito)
    return carrito


@router.patch("/items/{item_id}", response_model=CartPublic)
async def actualizar_item(
    item_id: int, 
    data: ItemCartUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    
    # Validar que la cantidad no sea negativa
    if data.cantidad < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cantidad no puede ser negativa"
        )
    
    # Si cantidad es 0, eliminar el item
    if data.cantidad == 0:
        item = _get_carrito_item(item_id, carrito.id, db)
        db.delete(item)
        carrito.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(carrito)
        return carrito
    
    # Actualizar cantidad
    item = _get_carrito_item(item_id, carrito.id, db)
    item.cantidad = data.cantidad
    carrito.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(carrito)
    return carrito


@router.delete("/items/{item_id}")
async def eliminar_item(
    item_id: int,  
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    item = _get_carrito_item(item_id, carrito.id, db)
    db.delete(item)
    carrito.updated_at = datetime.utcnow()
    db.commit()
    return {"detail": "Item eliminado del carrito"}


@router.delete("")
async def vaciar_carrito(
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: SessionDep,
):
    carrito = _get_or_create_carrito(current_user, db)
    for item in carrito.items[:]:  
        db.delete(item)
    carrito.updated_at = datetime.utcnow()
    db.commit()
    return {"detail": "Carrito vaciado"}