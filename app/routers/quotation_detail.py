from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response
from sqlmodel import select

from ..database import SessionDep
from ..models import Cotizacion, DetalleCotizacion, WoodPiece
from ..schemas import (
    DetalleCotizacionCreate,
    DetalleCotizacionPublic,
    DetalleCotizacionUpdate,
)

router = APIRouter(prefix="/cotizaciones/detalles", tags=["detalle_cotizacion"])


def _get_detalle_or_404(detalle_id: int, db: SessionDep) -> DetalleCotizacion:
    detalle = db.get(DetalleCotizacion, detalle_id)
    if not detalle:
        raise HTTPException(404, "Detalle de cotizacion no encontrado")
    return detalle


def _calcular_subtotal(precio_unitario: Decimal, cantidad: int) -> Decimal:
    return Decimal(str(precio_unitario)) * Decimal(str(cantidad))


@router.post("", response_model=DetalleCotizacionPublic, status_code=201)
async def crear_detalle(data: DetalleCotizacionCreate, db: SessionDep):
    cotizacion = db.get(Cotizacion, data.cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")

    pieza = db.get(WoodPiece, data.pieza_id)
    if not pieza:
        raise HTTPException(404, "Pieza no encontrada")

    subtotal = data.subtotal
    if subtotal is None:
        subtotal = _calcular_subtotal(
            data.precio_unitario_snapshot,
            data.cantidad,
        )

    detalle = DetalleCotizacion(
        cotizacion_id=data.cotizacion_id,
        pieza_id=data.pieza_id,
        descripcion_item=data.descripcion_item,
        cantidad=data.cantidad,
        volumen_unitario_m3=data.volumen_unitario_m3,
        precio_unitario_snapshot=data.precio_unitario_snapshot,
        subtotal=subtotal,
    )

    db.add(detalle)
    db.commit()
    db.refresh(detalle)
    return detalle


@router.get("", response_model=list[DetalleCotizacionPublic])
async def listar_detalles(db: SessionDep):
    return db.exec(select(DetalleCotizacion)).all()


@router.get("/cotizacion/{cotizacion_id}", response_model=list[DetalleCotizacionPublic])
async def listar_detalles_por_cotizacion(cotizacion_id: int, db: SessionDep):
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")

    query = select(DetalleCotizacion).where(
        DetalleCotizacion.cotizacion_id == cotizacion_id
    )
    return db.exec(query).all()


@router.get("/{detalle_id}", response_model=DetalleCotizacionPublic)
async def obtener_detalle(detalle_id: int, db: SessionDep):
    return _get_detalle_or_404(detalle_id, db)


# @router.get("/usuario/{user_id}", response_model=list[DetalleCotizacionPublic])
# async def get_user_details(user_id: int, db: SessionDep):
#     query = (
#         select(DetalleCotizacion)
#         .join(Cotizacion, DetalleCotizacion.cotizacion_id == Cotizacion.id)
#         .where(Cotizacion.user_id == user_id)
#     )
#     return db.exec(query).all()


@router.patch("/{detalle_id}", response_model=DetalleCotizacionPublic)
async def actualizar_detalle(
    detalle_id: int,
    data: DetalleCotizacionUpdate,
    db: SessionDep,
):
    detalle = _get_detalle_or_404(detalle_id, db)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    cantidad = update_data.get("cantidad", detalle.cantidad)
    precio = update_data.get(
        "precio_unitario_snapshot", detalle.precio_unitario_snapshot
    )
    if "subtotal" not in update_data and cantidad is not None and precio is not None:
        update_data["subtotal"] = _calcular_subtotal(precio, cantidad)

    detalle.sqlmodel_update(update_data)
    db.add(detalle)
    db.commit()
    db.refresh(detalle)
    return detalle


@router.delete("/{detalle_id}", status_code=204)
async def eliminar_detalle(detalle_id: int, db: SessionDep):
    detalle = _get_detalle_or_404(detalle_id, db)
    db.delete(detalle)
    db.commit()
    return Response(status_code=204)
