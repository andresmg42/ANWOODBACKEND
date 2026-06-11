from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select
from typing import Annotated

from ..auth import PermissionsEnum, get_current_active_user, require_permission
from ..database import SessionDep
from ..models import LoteInventory, MovimientoInventario, Proveedor, User
from ..schemas import (
    LoteCreate,
    LotePublic,
    MessageResponse,
    MovimientoInventarioPublic,
)

router = APIRouter(tags=["inventory"])


def _lote_query():
    return select(LoteInventory).options(selectinload(LoteInventory.proveedores))


def _get_lote_or_404(lote_id: int, db: SessionDep) -> LoteInventory:
    lote = db.exec(_lote_query().where(LoteInventory.id == lote_id)).unique().first()
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    return lote


def _asociar_proveedores(
    lote: LoteInventory, proveedor_ids: list[int], db: SessionDep
) -> None:
    if not proveedor_ids:
        return

    proveedores = db.exec(
        select(Proveedor).where(Proveedor.id.in_(proveedor_ids))
    ).all()
    if len(proveedores) != len(set(proveedor_ids)):
        raise HTTPException(400, "Uno o más proveedores no existen")

    lote.proveedores = proveedores


@router.post(
    "/lotes",
    response_model=LotePublic,
    status_code=201,
    summary="Crear lote",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_lote(data: LoteCreate, db: SessionDep):
    if db.exec(
        select(LoteInventory).where(LoteInventory.codigo_lote == data.codigo_lote)
    ).first():
        raise HTTPException(400, "El código de lote ya existe")

    lote_data = data.model_dump(exclude_unset=True, exclude={"proveedor_ids"})
    if lote_data.get("fecha_ingreso") is None:
        lote_data.pop("fecha_ingreso", None)

    lote = LoteInventory(**lote_data)
    db.add(lote)
    db.flush()
    _asociar_proveedores(lote, data.proveedor_ids, db)
    db.commit()

    return _get_lote_or_404(lote.id, db)


@router.get(
    "/lotes",
    response_model=list[LotePublic],
    summary="Listar lotes",
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def listar_lotes(db: SessionDep, estado: str = "activo"):
    query = _lote_query().where(LoteInventory.estado == estado)
    return db.exec(query).unique().all()


@router.get(
    "/lotes/{lote_id}",
    response_model=LotePublic,
    summary="Obtener lote por ID",
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def get_lote(lote_id: int, db: SessionDep):
    return _get_lote_or_404(lote_id, db)


@router.delete(
    "/lotes/{lote_id}",
    response_model=MessageResponse,
    summary="Desactivar lote",
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


@router.get(
    "/movimientos",
    response_model=list[MovimientoInventarioPublic],
    summary="Listar movimientos de inventario",
)
async def listar_movimientos(
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
    pieza_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
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
