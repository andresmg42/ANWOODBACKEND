from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from typing import Annotated
from sqlalchemy.orm import selectinload

from ..auth import require_permission, PermissionsEnum, get_current_active_user
from ..database import SessionDep
from ..models import WoodPiece, LoteInventory, MovimientoInventario, User
from ..models import Medida, TipoMadera  
from ..schemas import TipoMaderaPublic
from ..schemas import LoteCreate, LotePublic, PiezaCreate, PiezaPublic, PiezaUpdate, MovimientoInventarioPublic

router = APIRouter(tags=["inventory"])


# ─── Lotes ────────────────────────────────────────────────────────────────────

@router.post("/lotes", response_model=LotePublic, status_code=201,
             dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def crear_lote(data: LoteCreate, db: SessionDep):
    if db.exec(select(LoteInventory).where(LoteInventory.codigo_lote == data.codigo_lote)).first():
        raise HTTPException(400, "El código de lote ya existe")
    lote = LoteInventory.model_validate(data)
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


@router.get("/lotes", response_model=list[LotePublic],
            dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))])
async def listar_lotes(db: SessionDep, estado: str = "activo"):
    return db.exec(select(LoteInventory).where(LoteInventory.estado == estado)).all()


@router.get("/lotes/{lote_id}", response_model=LotePublic,
            dependencies=[Depends(require_permission(PermissionsEnum.VER_INVENTARIO))])
async def get_lote(lote_id: int, db: SessionDep):
    lote = db.get(LoteInventory, lote_id)
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    return lote


# ─── Piezas ───────────────────────────────────────────────────────────────────

def _calcular_volumen(medida: Medida, largo_mm: float) -> Decimal:
    """Ancho x Alto x Largo en mm³ → m³"""
    ancho = Decimal(medida.ancho_mm)
    alto = Decimal(medida.alto_mm)
    largo = Decimal(largo_mm)
    vol_mm3 = ancho * alto * largo
    return vol_mm3 / Decimal("1_000_000_000")


@router.post("/piezas", response_model=PiezaPublic, status_code=201,
             dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
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

    query = select(WoodPiece).where(WoodPiece.id == pieza.id).options(
        selectinload(WoodPiece.tipo_madera),
        selectinload(WoodPiece.medida)
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
        selectinload(WoodPiece.tipo_madera),
        selectinload(WoodPiece.medida)
    )
    if estado:
        q = q.where(WoodPiece.estado == estado)
    if tipo_madera_id:
        q = q.where(WoodPiece.tipo_madera_id == tipo_madera_id)

    return db.exec(q.offset(offset).limit(limit)).unique().all()


@router.get("/piezas/{pieza_id}", response_model=PiezaPublic)
async def get_pieza(pieza_id: int, db: SessionDep):
    query = select(WoodPiece).where(WoodPiece.id == pieza_id).options(
        selectinload(WoodPiece.tipo_madera),
        selectinload(WoodPiece.medida)
    )
    p = db.exec(query).unique().first()

    if not p:
        raise HTTPException(404, "Pieza no encontrada")

    return p


@router.patch("/piezas/{pieza_id}", response_model=PiezaPublic,
              dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def actualizar_pieza(pieza_id: int, data: PiezaUpdate, db: SessionDep):
    p = db.get(WoodPiece, pieza_id)
    if not p:
        raise HTTPException(404, "Pieza no encontrada")
    p.sqlmodel_update(data.model_dump(exclude_unset=True))
    db.commit()

    query = select(WoodPiece).where(WoodPiece.id == pieza_id).options(
        selectinload(WoodPiece.tipo_madera),
        selectinload(WoodPiece.medida)
    )
    return db.exec(query).unique().first()


@router.get("/movimientos", response_model=list[MovimientoInventarioPublic])
async def listar_movimientos(
    db: SessionDep,
    pieza_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    query = select(MovimientoInventario)

    if pieza_id:
        query = query.where(MovimientoInventario.pieza_id == pieza_id)

    query = query.order_by(MovimientoInventario.created_at.desc())
    query = query.offset(offset).limit(limit)

    movimientos = db.exec(query).all()

    result = []
    for mov in movimientos:
        mov_dict = mov.model_dump()
        if mov.usuario_id:
            usuario = db.get(User, mov.usuario_id)
            mov_dict["usuario_nombre"] = usuario.full_name if usuario else None
        else:
            mov_dict["usuario_nombre"] = None
        result.append(mov_dict)

    return result

# ─── Tipos de Madera ─────────────────────────────────────────────────────────

@router.get("/wood-types", response_model=list[TipoMaderaPublic])
async def listar_tipos_madera(db: SessionDep):
    return db.exec(select(TipoMadera)).all()

@router.post("/wood-types", 
             response_model=TipoMadera,
             dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def crear_tipo_madera(data: TipoMadera, db: SessionDep):
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

@router.post("/medidas", 
             response_model=Medida,
             dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))])
async def crear_medida(data: Medida, db: SessionDep):
    db.add(data)
    db.commit()
    db.refresh(data)
    return data