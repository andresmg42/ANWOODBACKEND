from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select

from ..auth import RoleEnum, get_current_active_user, require_role
from ..database import SessionDep
from ..models import Configuration, User
from ..schemas import (
    ConfigurationCreate,
    ConfigurationPublic,
    ConfigurationUpdate,
)

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.post(
    "/",
    response_model=ConfigurationPublic,
    status_code=201,
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def crear_configuracion(
    data: ConfigurationCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    existente = db.exec(
        select(Configuration).where(Configuration.clave == data.clave)
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="La clave ya existe")

    config = Configuration(
        **data.model_dump(),
        updated_by_id=current_user.id,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get(
    "/",
    response_model=list[ConfigurationPublic],
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def listar_configuracion(db: SessionDep):
    return db.exec(select(Configuration)).all()


@router.get(
    "/{config_id}",
    response_model=ConfigurationPublic,
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def obtener_configuracion(config_id: int, db: SessionDep):
    config = db.get(Configuration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuracion no encontrada")
    return config


@router.patch(
    "/{config_id}",
    response_model=ConfigurationPublic,
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def actualizar_configuracion(
    config_id: int,
    data: ConfigurationUpdate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    config = db.get(Configuration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuracion no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")

    if "clave" in update_data:
        existente = db.exec(
            select(Configuration)
            .where(Configuration.clave == update_data["clave"])
            .where(Configuration.id != config_id)
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="La clave ya existe")

    update_data["updated_at"] = datetime.utcnow()
    update_data["updated_by_id"] = current_user.id
    config.sqlmodel_update(update_data)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.delete(
    "/{config_id}",
    status_code=204,
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def eliminar_configuracion(config_id: int, db: SessionDep):
    config = db.get(Configuration, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuracion no encontrada")
    db.delete(config)
    db.commit()
    return Response(status_code=204)


def create_configuration_seed(
    db: SessionDep, clave: str, valor: str, descripcion: str = None
):

    configuration = Configuration(clave=clave, valor=valor, descripcion=descripcion)
    db.add(configuration)
    db.commit()
    db.refresh(configuration)
