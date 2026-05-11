from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from ..database import SessionDep
from ..models import TipoMadera, Categoria
from ..schemas import TipoMaderaPublic
from ..auth import require_permission, PermissionsEnum

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

@router.post("/", response_model=TipoMaderaPublic, dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def crear_tipo(data: TipoMadera, db: SessionDep):
    categoria = db.get(Categoria, data.categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="La categoría especificada no existe")
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

@router.patch("/{tipo_id}", response_model=TipoMaderaPublic,
              dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def actualizar_tipo(tipo_id: int, data: dict, db: SessionDep):
    db_tipo = db.get(TipoMadera, tipo_id)
    if not db_tipo:
        raise HTTPException(404, "Tipo de madera no encontrado")
    
    # Si se intenta cambiar la categoría, validamos que la nueva exista
    if "categoria_id" in data:
        categoria = db.get(Categoria, data["categoria_id"])
        if not categoria:
            raise HTTPException(404, "La nueva categoría especificada no existe")

    for key, value in data.items():
        setattr(db_tipo, key, value)
    
    db.add(db_tipo)
    db.commit()
    db.refresh(db_tipo)
    return db_tipo

@router.delete("/{tipo_id}", status_code=204,
               dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def eliminar_tipo(tipo_id: int, db: SessionDep):
    db_tipo = db.get(TipoMadera, tipo_id)
    if not db_tipo:
        raise HTTPException(404, "Tipo de madera no encontrado")
    
    db.delete(db_tipo)
    db.commit()
    return Response(status_code=204)