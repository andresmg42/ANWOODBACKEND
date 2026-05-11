from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from ..database import SessionDep
from ..models import Categoria
from ..schemas import CategoriaPublic
from ..auth import require_permission, PermissionsEnum

router = APIRouter(prefix="/categorias", tags=["categorias"])

@router.get("/", response_model=list[CategoriaPublic])
async def listar_categorias(db: SessionDep):
    return db.exec(select(Categoria)).all()

@router.post("/", 
             response_model=CategoriaPublic, 
             status_code=201,
             dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def crear_categoria(data: Categoria, db: SessionDep):
    existente = db.exec(select(Categoria).where(Categoria.nombre == data.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

@router.get("/{categoria_id}", response_model=CategoriaPublic)
async def obtener_categoria(categoria_id: int, db: SessionDep):
    cat = db.get(Categoria, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat

@router.patch("/{categoria_id}", response_model=CategoriaPublic,
              dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def actualizar_categoria(categoria_id: int, data: dict, db: SessionDep):
    db_cat = db.get(Categoria, categoria_id)
    if not db_cat:
        raise HTTPException(404, "Categoría no encontrada")
    
    cat_data = data # O usa un esquema de Update si prefieres
    for key, value in cat_data.items():
        setattr(db_cat, key, value)
    
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/{categoria_id}", status_code=204,
               dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def eliminar_categoria(categoria_id: int, db: SessionDep):
    db_cat = db.get(Categoria, categoria_id)
    if not db_cat:
        raise HTTPException(404, "Categoría no encontrada")
    
    db.delete(db_cat)
    db.commit()
    return Response(status_code=204)