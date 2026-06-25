from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import select
from typing import Annotated

from ..auth import require_permission, PermissionsEnum, get_current_active_user
from ..database import SessionDep
from ..models import Medida, MovimientoInventario, TipoMadera, User, WoodPiece
from ..schemas import MessageResponse, PiezaCreate, PiezaPublic, PiezaUpdate
from ..services.cotizacion_service import calcular_volumen, resolver_dimensiones_pieza

router = APIRouter(tags=["pieza_madera"])


@router.post(
    "/piezas",
    response_model=PiezaPublic,
    status_code=201,
    summary="Crear pieza de madera",
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

    query_tipo = (
        select(TipoMadera)
        .where(TipoMadera.id == data.tipo_madera_id)
        .options(selectinload(TipoMadera.categoria))
    )
    tipo_madera = db.exec(query_tipo).first()
    if not tipo_madera:
        raise HTTPException(404, "Tipo de madera no encontrado")
    categoria = tipo_madera.categoria
    if not categoria:
        raise HTTPException(400, "El tipo de madera no tiene categoría asociada")

    ancho_in, alto_in = resolver_dimensiones_pieza(
        medida, data.ancho_in, data.alto_in
    )
    volumen = calcular_volumen(
        medida, data.largo_m, categoria, tipo_madera, ancho_in, alto_in
    )

    pieza_data = data.model_dump()
    pieza_data["ancho_in"] = ancho_in
    pieza_data["alto_in"] = alto_in
    pieza = WoodPiece(**pieza_data, volumen_m3=volumen)
    db.add(pieza)
    db.flush()

    movimiento = MovimientoInventario(
        pieza_id=pieza.id,
        usuario_id=current_user.id,
        tipo_movimiento="ingreso",
        cantidad=data.cantidad,
    )
    db.add(movimiento)
    db.commit()

    query = (
        select(WoodPiece)
        .where(WoodPiece.id == pieza.id)
        .options(selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida))
    )
    return db.exec(query).unique().first()


@router.get(
    "/piezas",
    response_model=list[PiezaPublic],
    summary="Listar piezas de madera",
)
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


@router.get(
    "/piezas/{pieza_id}",
    response_model=PiezaPublic,
    summary="Obtener pieza por ID",
)
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
    summary="Actualizar pieza",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def actualizar_pieza(pieza_id: int, data: PiezaUpdate, db: SessionDep):
    p = db.get(WoodPiece, pieza_id)
    if not p:
        raise HTTPException(404, "Pieza no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    dimension_fields = {"largo_m", "ancho_in", "alto_in"}
    if dimension_fields & update_data.keys():
        medida = db.get(Medida, p.medida_id)
        tipo_query = (
            select(TipoMadera)
            .where(TipoMadera.id == p.tipo_madera_id)
            .options(selectinload(TipoMadera.categoria))
        )
        tipo_madera = db.exec(tipo_query).first()
        if not medida or not tipo_madera or not tipo_madera.categoria:
            raise HTTPException(400, "No fue posible recalcular el volumen de la pieza")

        largo_m = update_data.get("largo_m", p.largo_m)
        ancho_in, alto_in = resolver_dimensiones_pieza(
            medida,
            update_data.get("ancho_in", p.ancho_in),
            update_data.get("alto_in", p.alto_in),
        )
        update_data["ancho_in"] = ancho_in
        update_data["alto_in"] = alto_in
        update_data["volumen_m3"] = calcular_volumen(
            medida,
            largo_m,
            tipo_madera.categoria,
            tipo_madera,
            ancho_in,
            alto_in,
        )

    p.sqlmodel_update(update_data)
    db.commit()

    query = (
        select(WoodPiece)
        .where(WoodPiece.id == pieza_id)
        .options(selectinload(WoodPiece.tipo_madera), selectinload(WoodPiece.medida))
    )
    return db.exec(query).unique().first()


@router.delete(
    "/piezas/{pieza_id}",
    response_model=MessageResponse,
    summary="Desactivar pieza",
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