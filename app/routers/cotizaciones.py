from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..auth import (
    PermissionsEnum,
    get_current_active_user,
    require_permission,
)
from ..database import SessionDep
from ..models import (
    Client,
    Cotizacion,
    DetalleCotizacion,
    EstadoCotizacionEnum,
    Medida,
    TipoMadera,
    User,
    WoodPiece,
)
from ..schemas import (
    CotizacionCreate,
    CotizacionEstadoUpdate,
    CotizacionPreviewIn,
    CotizacionPreviewOut,
    CotizacionPublic,
    CotizacionUpdate,
    DetalleCotizacionCreate,
    DetalleCotizacionPublic,
)
from ..services.cotizacion_service import (
    construir_detalle_cotizacion,
    recalcular_cotizacion,
)

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


def _get_client_or_404(cliente_id: int, db: SessionDep) -> Client:
    cliente = db.get(Client, cliente_id)
    if not cliente or not cliente.activo:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


def _get_cotizacion_or_404(cotizacion_id: int, db: SessionDep) -> Cotizacion:
    query = (
        select(Cotizacion)
        .where(Cotizacion.id == cotizacion_id)
        .options(
            selectinload(Cotizacion.detalles).selectinload(DetalleCotizacion.medida),
            selectinload(Cotizacion.detalles).selectinload(
                DetalleCotizacion.tipo_madera
            ).selectinload(TipoMadera.categoria),
        )
    )
    cotizacion = db.exec(query).unique().first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cotizacion


def _get_tipo_madera_or_404(tipo_madera_id: int, db: SessionDep) -> TipoMadera:
    query = (
        select(TipoMadera)
        .where(TipoMadera.id == tipo_madera_id)
        .options(selectinload(TipoMadera.categoria))
    )
    tipo_madera = db.exec(query).first()
    if not tipo_madera:
        raise HTTPException(status_code=404, detail="Tipo de madera no encontrado")
    if not tipo_madera.categoria:
        raise HTTPException(
            status_code=400, detail="El tipo de madera no tiene categoría asociada"
        )
    return tipo_madera


def _validar_wood_piece(detalle: DetalleCotizacionCreate, db: SessionDep):
    if detalle.wood_piece_id is None:
        return

    pieza = db.get(WoodPiece, detalle.wood_piece_id)
    if not pieza:
        raise HTTPException(status_code=404, detail="Pieza de inventario no encontrada")
    if pieza.tipo_madera_id != detalle.tipo_madera_id:
        raise HTTPException(
            status_code=400,
            detail="La pieza seleccionada no coincide con el tipo de madera",
        )
    if pieza.medida_id != detalle.medida_id:
        raise HTTPException(
            status_code=400,
            detail="La pieza seleccionada no coincide con la medida",
        )


def _construir_detalles(
    cotizacion_id: int,
    detalles_in: list[DetalleCotizacionCreate],
    db: SessionDep,
) -> list[DetalleCotizacion]:
    detalles: list[DetalleCotizacion] = []
    for detalle_in in detalles_in:
        medida = db.get(Medida, detalle_in.medida_id)
        if not medida:
            raise HTTPException(status_code=404, detail="Medida no encontrada")

        tipo_madera = _get_tipo_madera_or_404(detalle_in.tipo_madera_id, db)
        _validar_wood_piece(detalle_in, db)

        detalle = construir_detalle_cotizacion(
            cotizacion_id=cotizacion_id,
            detalle_in=detalle_in,
            medida=medida,
            tipo_madera=tipo_madera,
            categoria=tipo_madera.categoria,
        )
        detalle.medida = medida
        detalle.tipo_madera = tipo_madera
        detalles.append(detalle)
    return detalles


@router.post(
    "/preview",
    response_model=CotizacionPreviewOut,
    dependencies=[Depends(require_permission(PermissionsEnum.CREATE_COTIZACION))],
)
async def preview_cotizacion(
    data: CotizacionPreviewIn,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    _get_client_or_404(data.cliente_id, db)

    cotizacion = Cotizacion(
        cliente_id=data.cliente_id,
        usuario_id=current_user.id,
        porcentaje_anticipo=data.porcentaje_anticipo,
        notas=data.notas,
    )
    detalles = _construir_detalles(0, data.detalles, db)
    recalcular_cotizacion(cotizacion, detalles, db, cost_source=data)

    return CotizacionPreviewOut(
        subtotal_piezas=cotizacion.subtotal_piezas,
        metros_totales=cotizacion.metros_totales,
        costo_cargue_terrestre=cotizacion.costo_cargue_terrestre,
        costo_descargue_terrestre=cotizacion.costo_descargue_terrestre,
        costo_cargue_maritimo=cotizacion.costo_cargue_maritimo,
        costo_descargue_maritimo=cotizacion.costo_descargue_maritimo,
        costo_salvoconducto_epa=cotizacion.costo_salvoconducto_epa,
        precio_epa_por_metro_usado=cotizacion.precio_epa_por_metro_usado,
        total=cotizacion.total,
        porcentaje_anticipo=cotizacion.porcentaje_anticipo,
        monto_anticipo=cotizacion.monto_anticipo,
        detalles=[
            DetalleCotizacionPublic.model_validate(detalle, from_attributes=True)
            for detalle in detalles
        ],
    )


@router.post(
    "",
    response_model=CotizacionPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PermissionsEnum.CREATE_COTIZACION))],
)
async def crear_cotizacion(
    data: CotizacionCreate,
    db: SessionDep,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    _get_client_or_404(data.cliente_id, db)

    cotizacion = Cotizacion(
        cliente_id=data.cliente_id,
        usuario_id=current_user.id,
        porcentaje_anticipo=data.porcentaje_anticipo,
        notas=data.notas,
    )
    db.add(cotizacion)
    db.flush()

    detalles = _construir_detalles(cotizacion.id, data.detalles, db)
    for detalle in detalles:
        db.add(detalle)

    recalcular_cotizacion(cotizacion, detalles, db, cost_source=data)
    db.add(cotizacion)
    db.commit()
    return _get_cotizacion_or_404(cotizacion.id, db)


@router.get(
    "",
    response_model=list[CotizacionPublic],
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_COTIZACION))],
)
async def listar_cotizaciones(
    db: SessionDep,
    cliente_id: int | None = None,
    estado: str | None = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=200)] = 100,
):
    query = select(Cotizacion).options(
        selectinload(Cotizacion.detalles).selectinload(DetalleCotizacion.medida),
        selectinload(Cotizacion.detalles)
        .selectinload(DetalleCotizacion.tipo_madera)
        .selectinload(TipoMadera.categoria),
    )
    if cliente_id is not None:
        query = query.where(Cotizacion.cliente_id == cliente_id)
    if estado:
        query = query.where(Cotizacion.estado == estado)

    query = query.order_by(Cotizacion.fecha_creacion.desc()).offset(offset).limit(limit)
    return db.exec(query).unique().all()


@router.get(
    "/{cotizacion_id}",
    response_model=CotizacionPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_COTIZACION))],
)
async def obtener_cotizacion(cotizacion_id: int, db: SessionDep):
    return _get_cotizacion_or_404(cotizacion_id, db)


@router.patch(
    "/{cotizacion_id}",
    response_model=CotizacionPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_COTIZACION))],
)
async def actualizar_cotizacion(
    cotizacion_id: int,
    data: CotizacionUpdate,
    db: SessionDep,
):
    cotizacion = _get_cotizacion_or_404(cotizacion_id, db)
    update_data = data.model_dump(exclude_unset=True)
    if "porcentaje_anticipo" in update_data:
        cotizacion.porcentaje_anticipo = update_data["porcentaje_anticipo"]
    if "notas" in update_data:
        cotizacion.notas = update_data["notas"]

    detalles = cotizacion.detalles
    if data.detalles is not None:
        for detalle_existente in cotizacion.detalles:
            db.delete(detalle_existente)
        db.flush()
        detalles = _construir_detalles(cotizacion.id, data.detalles, db)
        for detalle in detalles:
            db.add(detalle)

    cotizacion.fecha_actualizacion = datetime.utcnow()
    recalcular_cotizacion(cotizacion, detalles, db, cost_source=data)
    db.add(cotizacion)
    db.commit()
    return _get_cotizacion_or_404(cotizacion_id, db)


@router.post(
    "/{cotizacion_id}/detalles",
    response_model=CotizacionPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_COTIZACION))],
)
async def agregar_detalle_cotizacion(
    cotizacion_id: int,
    data: DetalleCotizacionCreate,
    db: SessionDep,
):
    cotizacion = _get_cotizacion_or_404(cotizacion_id, db)
    detalles_nuevos = _construir_detalles(cotizacion.id, [data], db)
    detalle = detalles_nuevos[0]
    db.add(detalle)
    db.flush()

    detalles = [*cotizacion.detalles, detalle]
    cotizacion.fecha_actualizacion = datetime.utcnow()
    recalcular_cotizacion(cotizacion, detalles, db)
    db.add(cotizacion)
    db.commit()
    return _get_cotizacion_or_404(cotizacion_id, db)


@router.delete(
    "/{cotizacion_id}/detalles/{detalle_id}",
    response_model=CotizacionPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_COTIZACION))],
)
async def eliminar_detalle_cotizacion(
    cotizacion_id: int,
    detalle_id: int,
    db: SessionDep,
):
    cotizacion = _get_cotizacion_or_404(cotizacion_id, db)
    detalle = db.get(DetalleCotizacion, detalle_id)
    if not detalle or detalle.cotizacion_id != cotizacion.id:
        raise HTTPException(status_code=404, detail="Detalle de cotización no encontrado")

    db.delete(detalle)
    db.flush()

    detalles_restantes = [item for item in cotizacion.detalles if item.id != detalle_id]
    cotizacion.fecha_actualizacion = datetime.utcnow()
    recalcular_cotizacion(cotizacion, detalles_restantes, db)
    db.add(cotizacion)
    db.commit()
    return _get_cotizacion_or_404(cotizacion_id, db)


@router.patch(
    "/{cotizacion_id}/estado",
    response_model=CotizacionPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.APROBAR_COTIZACION))],
)
async def actualizar_estado_cotizacion(
    cotizacion_id: int,
    data: CotizacionEstadoUpdate,
    db: SessionDep,
):
    cotizacion = _get_cotizacion_or_404(cotizacion_id, db)
    estados_validos = {estado.value for estado in EstadoCotizacionEnum}
    if data.estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado de cotización inválido")

    cotizacion.estado = data.estado
    cotizacion.fecha_actualizacion = datetime.utcnow()
    db.add(cotizacion)
    db.commit()
    return _get_cotizacion_or_404(cotizacion_id, db)


@router.delete(
    "/{cotizacion_id}",
    status_code=204,
    dependencies=[Depends(require_permission(PermissionsEnum.DELETE_COTIZACION))],
)
async def eliminar_cotizacion(cotizacion_id: int, db: SessionDep):
    cotizacion = _get_cotizacion_or_404(cotizacion_id, db)
    cotizacion.estado = EstadoCotizacionEnum.CANCELADA.value
    cotizacion.fecha_actualizacion = datetime.utcnow()
    db.add(cotizacion)
    db.commit()
    return Response(status_code=204)
