from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select

from ..auth import PermissionsEnum, require_permission
from ..database import SessionDep
from ..models import Medida
from ..schemas import MedidaCreate, MedidaPublic, MedidaUpdate

router = APIRouter(prefix="/medidas", tags=["medidas"])


@router.get("/{medida_id}", response_model=MedidaPublic)
async def obtener_medida(medida_id: int, db: SessionDep):
    medida = db.get(Medida, medida_id)
    if not medida:
        raise HTTPException(404, "Medida no encontrada")
    return medida


@router.get("/", response_model=list[MedidaPublic])
async def listar_medidas(db: SessionDep):
    return db.exec(select(Medida)).all()


@router.post(
    "/",
    response_model=MedidaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_medida(data: MedidaCreate, db: SessionDep):
    medida = Medida.model_validate(data)
    db.add(medida)
    db.commit()
    db.refresh(medida)
    return medida


@router.patch(
    "/{medida_id}",
    response_model=MedidaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_medida(medida_id: int, data: MedidaUpdate, db: SessionDep):
    db_medida = db.get(Medida, medida_id)
    if not db_medida:
        raise HTTPException(404, "Medida no encontrada")

    db_medida.sqlmodel_update(data.model_dump(exclude_unset=True))
    db.add(db_medida)
    db.commit()
    db.refresh(db_medida)
    return db_medida


@router.delete(
    "/{medida_id}",
    status_code=204,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def eliminar_medida(medida_id: int, db: SessionDep):
    db_medida = db.get(Medida, medida_id)
    if not db_medida:
        raise HTTPException(404, "Medida no encontrada")

    db.delete(db_medida)
    db.commit()
    return Response(status_code=204)
