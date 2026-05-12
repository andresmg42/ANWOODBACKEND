from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select

from ..auth import PermissionsEnum, require_permission
from ..database import SessionDep
from ..models import Categoria
from ..schemas import CategoriaCreate, CategoriaPublic, CategoriaUpdate

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("/", response_model=list[CategoriaPublic])
async def listar_categorias(db: SessionDep):
    return db.exec(select(Categoria)).all()


@router.post(
    "/",
    response_model=CategoriaPublic,
    status_code=201,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_categoria(data: CategoriaCreate, db: SessionDep):
    existente = db.exec(select(Categoria).where(Categoria.nombre == data.nombre)).first()
    if existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")

    categoria = Categoria.model_validate(data)
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.get("/{categoria_id}", response_model=CategoriaPublic)
async def obtener_categoria(categoria_id: int, db: SessionDep):
    cat = db.get(Categoria, categoria_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat


@router.patch(
    "/{categoria_id}",
    response_model=CategoriaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_categoria(categoria_id: int, data: CategoriaUpdate, db: SessionDep):
    db_cat = db.get(Categoria, categoria_id)
    if not db_cat:
        raise HTTPException(404, "Categoría no encontrada")

    db_cat.sqlmodel_update(data.model_dump(exclude_unset=True))
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


@router.delete(
    "/{categoria_id}",
    status_code=204,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def eliminar_categoria(categoria_id: int, db: SessionDep):
    db_cat = db.get(Categoria, categoria_id)
    if not db_cat:
        raise HTTPException(404, "Categoría no encontrada")

    db.delete(db_cat)
    db.commit()
    return Response(status_code=204)