from fastapi import APIRouter, HTTPException
from sqlmodel import select
from fastapi import Depends, HTTPException
from ..database import SessionDep
from ..models import Client, User
from ..schemas import ClientCreate, ClientPublic, ClientUpdate
from ..auth import (
    require_permission,
    PermissionsEnum,
)

router = APIRouter(tags=["client"])


@router.post("/clientes", response_model=ClientPublic, status_code=201)
async def crear_cliente(data: ClientCreate, db: SessionDep):
    if not db.get(User, data.usuario_id):
        raise HTTPException(404, "Usuario no encontrado")
    cliente = Client.model_validate(data)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get(
    "/clientes",
    response_model=list[ClientPublic],
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def listar_clientes(db: SessionDep, activo: bool | None = True):
    query = select(Client)
    if activo is not None:
        query = query.where(Client.activo == activo)
    return db.exec(query).all()


@router.get(
    "/clientes/{cliente_id}",
    response_model=ClientPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def get_cliente(cliente_id: int, db: SessionDep):
    cliente = db.get(Client, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente


@router.patch(
    "/clientes/{cliente_id}",
    response_model=ClientPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_USER))],
)
async def actualizar_cliente(cliente_id: int, data: ClientUpdate, db: SessionDep):
    cliente = db.get(Client, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
    if "usuario_id" in update_data and not db.get(User, update_data["usuario_id"]):
        raise HTTPException(404, "Usuario no encontrado")
    cliente.sqlmodel_update(update_data)
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete(
    "/clientes/{cliente_id}",
    dependencies=[Depends(require_permission(PermissionsEnum.DELETE_USER))],
)
async def eliminar_cliente(cliente_id: int, db: SessionDep):
    cliente = db.get(Client, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    if not cliente.activo:
        return {"message": f"Cliente con id {cliente_id} ya esta inactivo"}
    cliente.activo = False
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return {"message": f"Cliente con id {cliente_id} eliminado"}
