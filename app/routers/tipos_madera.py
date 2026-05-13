from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select

from ..auth import PermissionsEnum, require_permission
from ..database import SessionDep
from ..models import Categoria, TipoMadera
from ..schemas import TipoMaderaCreate, TipoMaderaPublic, TipoMaderaUpdate

router = APIRouter(prefix="/wood-types", tags=["wood-types"])


@router.get("/", response_model=list[TipoMaderaPublic])
async def listar_tipos(db: SessionDep):
    return db.exec(select(TipoMadera)).all()


@router.get("/{tipo_id}", response_model=TipoMaderaPublic)
async def obtener_tipo(tipo_id: int, db: SessionDep):
    tipo = db.get(TipoMadera, tipo_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de madera no encontrado")
    return tipo


@router.post(
    "/",
    response_model=TipoMaderaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_tipo(data: TipoMaderaCreate, db: SessionDep):
    categoria = db.get(Categoria, data.categoria_id)
    if not categoria:
        raise HTTPException(
            status_code=404, detail="La categoría especificada no existe"
        )

    tipo = TipoMadera.model_validate(data)
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.patch(
    "/{tipo_id}",
    response_model=TipoMaderaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_tipo(tipo_id: int, data: TipoMaderaUpdate, db: SessionDep):
    db_tipo = db.get(TipoMadera, tipo_id)
    if not db_tipo:
        raise HTTPException(404, "Tipo de madera no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    if "categoria_id" in update_data:
        categoria = db.get(Categoria, update_data["categoria_id"])
        if not categoria:
            raise HTTPException(404, "La nueva categoría especificada no existe")

    db_tipo.sqlmodel_update(update_data)
    db.add(db_tipo)
    db.commit()
    db.refresh(db_tipo)
    return db_tipo


@router.delete(
    "/{tipo_id}",
    status_code=204,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def eliminar_tipo(tipo_id: int, db: SessionDep):
    db_tipo = db.get(TipoMadera, tipo_id)
    if not db_tipo:
        raise HTTPException(404, "Tipo de madera no encontrado")

    db.delete(db_tipo)
    db.commit()
    return Response(status_code=204)