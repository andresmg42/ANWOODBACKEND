from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from typing import Annotated
from sqlalchemy.orm import selectinload

from ..auth import require_permission, PermissionsEnum, get_current_active_user
from ..database import SessionDep
from ..models import WoodPiece, MovimientoInventario, User
from ..models import Medida, TipoMadera
from ..schemas import (
    PiezaCreate,
    PiezaPublic,
    PiezaUpdate,
)

router = APIRouter(tags=["pieza_madera"])


def _calcular_volumen(medida: Medida, largo_mm: float) -> Decimal:
    """Ancho x Alto x Largo en mm³ → m³"""
    ancho = Decimal(medida.ancho_mm)
    alto = Decimal(medida.alto_mm)
    largo = Decimal(largo_mm)
    vol_mm3 = ancho * alto * largo
    return vol_mm3 / Decimal("1_000_000_000")


@router.post(
    "/piezas",
    response_model=PiezaPublic,
    status_code=201,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def crear_pieza(
    data: PiezaCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    medida = db.get(Medida, data.medida_id)
    if not medida:
        raise HTTPException(404, "Medida no encontrada")
    if not db.get(TipoMadera, data.tipo_madera_id):
        raise HTTPException(404, "Tipo de madera no encontrado")
    volumen = _calcular_volumen(medida, data.largo_mm)

    pieza = WoodPiece(**data.model_dump(), volumen_m3=volumen)
    db.add(pieza)
    db.flush()

    movimiento = MovimientoInventario(
        pieza_id=pieza.id,
        usuario_id=current_user.id,
        tipo_movimiento="ingreso",
        cantidad=1,
    )
    db.add(movimiento)
    db.commit()

    query = (
        select(WoodPiece)
        .where(WoodPiece.id == pieza.id)
        .options(selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida))
    )
    return db.exec(query).unique().first()


@router.get("/piezas", response_model=list[PiezaPublic])
async def listar_piezas(
    db: SessionDep,
    estado: str | None = None,
    tipo_madera_id: int | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=200)] = 100,
):
    q = select(WoodPiece).options(
        selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida)
    )
    if estado:
        q = q.where(WoodPiece.estado == estado)
    if tipo_madera_id:
        q = q.where(WoodPiece.tipo_madera_id == tipo_madera_id)

    return db.exec(q.offset(offset).limit(limit)).unique().all()


@router.get("/piezas/{pieza_id}", response_model=PiezaPublic)
async def get_pieza(pieza_id: int, db: SessionDep):
    query = (
        select(WoodPiece)
        .where(WoodPiece.id == pieza_id)
        .options(selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida))
    )
    p = db.exec(query).unique().first()

    if not p:
        raise HTTPException(404, "Pieza no encontrada")

    return p


@router.patch(
    "/piezas/{pieza_id}",
    response_model=PiezaPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_pieza(pieza_id: int, data: PiezaUpdate, db: SessionDep):
    p = db.get(WoodPiece, pieza_id)
    if not p:
        raise HTTPException(404, "Pieza no encontrada")
    p.sqlmodel_update(data.model_dump(exclude_unset=True))
    db.commit()

    query = (
        select(WoodPiece)
        .where(WoodPiece.id == pieza_id)
        .options(selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida))
    )
    return db.exec(query).unique().first()


@router.delete(
    "/piezas/{pieza_id}",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def eliminar_pieza(pieza_id: int, db: SessionDep):
    p = db.get(WoodPiece, pieza_id)
    if not p:
        raise HTTPException(404, "Pieza no encontrada")
    if p.estado != "disponible":
        return {"message": f"Pieza con id {pieza_id} ya esta inactiva"}
    p.estado = "inactivo"
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"message": f"Pieza con id {pieza_id} eliminada"}
