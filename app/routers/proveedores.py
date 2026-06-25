from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select

from ..auth import PermissionsEnum, get_current_active_user, require_permission
from ..database import SessionDep
from ..models import Proveedor, User
from ..schemas import ProveedorCreate, ProveedorPublic, ProveedorUpdate

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


def _get_proveedor_or_404(proveedor_id: int, db: SessionDep) -> Proveedor:
    proveedor = db.get(Proveedor, proveedor_id)
    if not proveedor:
        raise HTTPException(404, "Proveedor no encontrado")
    return proveedor


@router.get(
    "/",
    response_model=list[ProveedorPublic],
    summary="Listar proveedores",
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def listar_proveedores(db: SessionDep, activo: bool | None = None):
    query = select(Proveedor)
    if activo is not None:
        query = query.where(Proveedor.activo == activo)
    return db.exec(query).all()


@router.get(
    "/{proveedor_id}",
    response_model=ProveedorPublic,
    summary="Obtener proveedor por ID",
    dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))],
)
async def obtener_proveedor(proveedor_id: int, db: SessionDep):
    return _get_proveedor_or_404(proveedor_id, db)


@router.post(
    "/",
    response_model=ProveedorPublic,
    status_code=201,
    summary="Crear proveedor",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_proveedor(
    data: ProveedorCreate,
    db: SessionDep,
    _current_user: Annotated[User, Depends(get_current_active_user)],
):
    if data.user_id is not None:
        user = db.get(User, data.user_id)
        if not user:
            raise HTTPException(404, "Usuario no encontrado")
        existente = db.exec(
            select(Proveedor).where(Proveedor.user_id == data.user_id)
        ).first()
        if existente:
            raise HTTPException(400, "El usuario ya está asociado a un proveedor")

    proveedor = Proveedor(**data.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.patch(
    "/{proveedor_id}",
    response_model=ProveedorPublic,
    summary="Actualizar proveedor",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_proveedor(
    proveedor_id: int,
    data: ProveedorUpdate,
    db: SessionDep,
):
    proveedor = _get_proveedor_or_404(proveedor_id, db)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(400, "No hay datos para actualizar")

    if "user_id" in update_data and update_data["user_id"] is not None:
        user = db.get(User, update_data["user_id"])
        if not user:
            raise HTTPException(404, "Usuario no encontrado")
        existente = db.exec(
            select(Proveedor)
            .where(Proveedor.user_id == update_data["user_id"])
            .where(Proveedor.id != proveedor_id)
        ).first()
        if existente:
            raise HTTPException(400, "El usuario ya está asociado a otro proveedor")

    proveedor.sqlmodel_update(update_data)
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.delete(
    "/{proveedor_id}",
    status_code=204,
    summary="Desactivar proveedor",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def desactivar_proveedor(proveedor_id: int, db: SessionDep):
    proveedor = _get_proveedor_or_404(proveedor_id, db)
    proveedor.activo = False
    db.add(proveedor)
    db.commit()
    return Response(status_code=204)
