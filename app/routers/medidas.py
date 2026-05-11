from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from ..database import SessionDep
from ..models import Medida
from ..auth import require_permission, PermissionsEnum

router = APIRouter(prefix="/medidas", tags=["medidas"])


@router.get("/{medida_id}", response_model=Medida)
async def obtener_medida(medida_id: int, db: SessionDep):
    medida = db.get(Medida, medida_id)
    if not medida:
        raise HTTPException(404, "Medida no encontrada")
    return medida


@router.get("/", response_model=list[Medida])
async def listar_medidas(db: SessionDep):
    return db.exec(select(Medida)).all()


@router.post(
    "/",
    response_model=Medida,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_medida(data: Medida, db: SessionDep):
    db.add(data)
    db.commit()
    db.refresh(data)
    return data


@router.patch(
    "/{medida_id}",
    response_model=Medida,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_medida(medida_id: int, data: dict, db: SessionDep):
    db_medida = db.get(Medida, medida_id)
    if not db_medida:
        raise HTTPException(404, "Medida no encontrada")

    for key, value in data.items():
        setattr(db_medida, key, value)

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
