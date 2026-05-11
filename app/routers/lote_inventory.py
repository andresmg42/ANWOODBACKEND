from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from typing import Annotated
from ..auth import require_permission, PermissionsEnum, get_current_active_user
from ..database import SessionDep
from ..models import LoteInventory, MovimientoInventario, User
from ..schemas import (
    LoteCreate,
    LotePublic,
    MovimientoInventarioPublic,
)

router = APIRouter(tags=["inventory"])


@router.post(
    "/lotes",
    response_model=LotePublic,
    status_code=201,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_lote(data: LoteCreate, db: SessionDep):
    if db.exec(
        select(LoteInventory).where(LoteInventory.codigo_lote == data.codigo_lote)
    ).first():
        raise HTTPException(400, "El código de lote ya existe")
    lote = LoteInventory.model_validate(data)
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


@router.get(
    "/lotes",
    response_model=list[LotePublic],
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def listar_lotes(db: SessionDep, estado: str = "activo"):
    return db.exec(select(LoteInventory).where(LoteInventory.estado == estado)).all()


@router.get(
    "/lotes/{lote_id}",
    response_model=LotePublic,
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def get_lote(lote_id: int, db: SessionDep):
    lote = db.get(LoteInventory, lote_id)
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    return lote


@router.delete(
    "/lotes/{lote_id}",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def eliminar_lote(lote_id: int, db: SessionDep):
    lote = db.get(LoteInventory, lote_id)
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    if lote.estado != "activo":
        return {"message": f"Lote con id {lote_id} ya esta inactivo"}
    lote.estado = "inactivo"
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return {"message": f"Lote con id {lote_id} eliminado"}


@router.get("/movimientos", response_model=list[MovimientoInventarioPublic])
async def listar_movimientos(
    db: SessionDep,
    pieza_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    query = select(MovimientoInventario)

    if pieza_id:
        query = query.where(MovimientoInventario.pieza_id == pieza_id)

    query = query.order_by(MovimientoInventario.created_at.desc())
    query = query.offset(offset).limit(limit)

    movimientos = db.exec(query).all()

    result = []
    for mov in movimientos:
        mov_dict = mov.model_dump()
        if mov.usuario_id:
            usuario = db.get(User, mov.usuario_id)
            mov_dict["usuario_nombre"] = usuario.full_name if usuario else None
        else:
            mov_dict["usuario_nombre"] = None
        result.append(mov_dict)

    return result