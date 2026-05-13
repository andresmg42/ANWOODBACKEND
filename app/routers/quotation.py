from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlalchemy import func
from ..auth import PermissionsEnum, require_permission
from ..database import SessionDep
from ..models import (
    Cart,
    Configuration,
    Cotizacion,
    DetalleCotizacion,
    ItemCart,
    WoodPiece,
)
from ..schemas import CotizacionCreate, CotizacionPublic, CotizacionUpdate

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


def _get_config_decimal(
    db: SessionDep, key: str, default: Decimal | None = None, required: bool = True
) -> Decimal:
    config = db.exec(select(Configuration).where(Configuration.clave == key)).first()
    if not config or config.valor is None:
        if required:
            raise HTTPException(400, f"Missing configuracion: {key}")
        return default or Decimal("0")
    try:
        return Decimal(str(config.valor))
    except Exception:
        raise HTTPException(400, f"Invalid configuracion value for {key}")


def _get_config_int(
    db: SessionDep, key: str, default: int | None = None, required: bool = True
) -> int:
    config = db.exec(select(Configuration).where(Configuration.clave == key)).first()
    if not config or config.valor is None:
        if required:
            raise HTTPException(400, f"Missing configuracion: {key}")
        return default or 0
    try:
        return int(Decimal(str(config.valor)))
    except Exception:
        raise HTTPException(400, f"Invalid configuracion value for {key}")


def _get_cart_items_for_user(db: SessionDep, user_id: int) -> list[ItemCart]:
    carrito = db.exec(select(Cart).where(Cart.user_id == user_id)).first()
    if not carrito:
        raise HTTPException(400, "El usuario no tiene carrito")

    items = db.exec(select(ItemCart).where(ItemCart.carrito_id == carrito.id)).all()
    if not items:
        raise HTTPException(400, "El carrito esta vacio")

    return items


def _calcular_totales_desde_carrito(
    db: SessionDep, items: list[ItemCart]
) -> tuple[Decimal, Decimal]:
    total_m3 = Decimal("0")
    subtotal = Decimal("0")

    for item in items:
        pieza = db.get(WoodPiece, item.wood_piece_id)
        if not pieza:
            raise HTTPException(404, "Pieza no encontrada en el carrito")
        if pieza.volumen_m3 is None:
            raise HTTPException(400, "La pieza no tiene volumen calculado")
        if pieza.precio_unitario is None:
            raise HTTPException(400, "La pieza no tiene precio unitario")

        cantidad = Decimal(str(item.cantidad or 0))
        total_m3 += Decimal(str(pieza.volumen_m3)) * cantidad
        subtotal += Decimal(str(pieza.precio_unitario)) * cantidad

    return total_m3, subtotal


def _crear_detalles_desde_carrito(
    db: SessionDep, cotizacion_id: int, items: list[ItemCart]
) -> None:
    for item in items:
        pieza = db.get(WoodPiece, item.wood_piece_id)
        if not pieza:
            raise HTTPException(404, "Pieza no encontrada en el carrito")
        if pieza.volumen_m3 is None:
            raise HTTPException(400, "La pieza no tiene volumen calculado")
        if pieza.precio_unitario is None:
            raise HTTPException(400, "La pieza no tiene precio unitario")

        cantidad = int(item.cantidad or 0)
        precio_unitario = Decimal(str(pieza.precio_unitario))
        subtotal = precio_unitario * Decimal(str(cantidad))

        detalle = DetalleCotizacion(
            cotizacion_id=cotizacion_id,
            pieza_id=pieza.id,
            descripcion_item=f"Pieza {pieza.id}",
            cantidad=cantidad,
            volumen_unitario_m3=Decimal(str(pieza.volumen_m3)),
            precio_unitario_snapshot=precio_unitario,
            subtotal=subtotal,
        )
        db.add(detalle)


def _calcular_valores_derivados(
    total_m3: Decimal,
    subtotal: Decimal,
    porcentaje_anticipo: Decimal,
    costo_transporte: Decimal,
    costo_cargue: Decimal,
    costo_descargue: Decimal,
    costo_salvoconducto: Decimal,
) -> tuple[Decimal, Decimal]:
    valor_anticipo = subtotal * (porcentaje_anticipo / Decimal("100"))
    total_monto = (
        subtotal
        + costo_transporte
        + costo_cargue
        + costo_descargue
        + costo_salvoconducto
    )
    return valor_anticipo, total_monto


def generate_numero_cotizacion(db: SessionDep) -> str:
    year = datetime.utcnow().year
    result = db.exec(
        select(func.count(Cotizacion.id)).where(
            func.extract("year", Cotizacion.created_at) == year
        )
    )
    count = (result.one() or 0) + 1
    return f"COT-{year}-{str(count).zfill(4)}"


@router.post(
    "",
    response_model=CotizacionPublic,
    status_code=201,
    # dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def crear_cotizacion(
    data: CotizacionCreate,
    db: SessionDep,
):
    existente = db.exec(
        select(Cotizacion).where(Cotizacion.numero_cotizacion == data.numero_cotizacion)
    ).first()
    if existente:
        raise HTTPException(400, "El numero de cotizacion ya existe")

    items = _get_cart_items_for_user(db, data.user_id)
    total_m3, subtotal = _calcular_totales_desde_carrito(db, items)

    porcentaje_anticipo = _get_config_decimal(db, "porcentaje_anticipo")
    tasa_salvoconducto = _get_config_decimal(db, "tasa_salvoconducto_por_m3")
    dias_vencimiento = _get_config_int(db, "dias_vencimiento_cotizacion")
    costo_transporte_default = _get_config_decimal(
        db, "costo_transporte_defecto", required=False, default=Decimal("0")
    )
    costo_cargue_default = _get_config_decimal(
        db, "costo_cargue_defecto", required=False, default=Decimal("0")
    )
    costo_descargue_default = _get_config_decimal(
        db, "costo_descargue_defecto", required=False, default=Decimal("0")
    )

    costo_transporte = (
        data.costo_transporte
        if data.costo_transporte is not None
        else costo_transporte_default
    )
    costo_cargue = (
        data.costo_cargue if data.costo_cargue is not None else costo_cargue_default
    )
    costo_descargue = (
        data.costo_descargue
        if data.costo_descargue is not None
        else costo_descargue_default
    )

    costo_salvoconducto = total_m3 * tasa_salvoconducto
    valor_anticipo, total_monto = _calcular_valores_derivados(
        total_m3=total_m3,
        subtotal=subtotal,
        porcentaje_anticipo=porcentaje_anticipo,
        costo_transporte=Decimal(str(costo_transporte)),
        costo_cargue=Decimal(str(costo_cargue)),
        costo_descargue=Decimal(str(costo_descargue)),
        costo_salvoconducto=costo_salvoconducto,
    )

    fecha_emision = datetime.utcnow()
    fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
    numero_cotizacion = generate_numero_cotizacion(db)
    cotizacion = Cotizacion(
        user_id=data.user_id,
        numero_cotizacion=numero_cotizacion,
        estado=data.estado or "pendiente",
        tipo_compra=data.tipo_compra,
        total_m3=total_m3,
        subtotal=subtotal,
        costo_transporte=Decimal(str(costo_transporte)),
        costo_cargue=Decimal(str(costo_cargue)),
        costo_descargue=Decimal(str(costo_descargue)),
        costo_salvoconducto=costo_salvoconducto,
        porcentaje_anticipo=porcentaje_anticipo,
        valor_anticipo=valor_anticipo,
        total_monto=total_monto,
        fecha_emision=fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        salvoconducto_es_manual=data.salvoconducto_es_manual or False,
    )

    db.add(cotizacion)
    db.flush()
    _crear_detalles_desde_carrito(db, cotizacion.id, items)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


@router.get(
    "",
    response_model=list[CotizacionPublic],
    # dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def listar_cotizaciones(db: SessionDep):
    return db.exec(select(Cotizacion)).all()


@router.get(
    "/{cotizacion_id}",
    response_model=CotizacionPublic,
    # dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def obtener_cotizacion(cotizacion_id: int, db: SessionDep):
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")
    return cotizacion


@router.patch(
    "/{cotizacion_id}",
    response_model=CotizacionPublic,
    # dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
async def actualizar_cotizacion(
    cotizacion_id: int,
    data: CotizacionUpdate,
    db: SessionDep,
):
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    recalcular = update_data.pop("recalcular", False)

    if recalcular:
        items = _get_cart_items_for_user(db, cotizacion.user_id)
        total_m3, subtotal = _calcular_totales_desde_carrito(db, items)

        porcentaje_anticipo = _get_config_decimal(db, "porcentaje_anticipo")
        tasa_salvoconducto = _get_config_decimal(db, "tasa_salvoconducto_por_m3")
        dias_vencimiento = _get_config_int(db, "dias_vencimiento_cotizacion")
        costo_transporte_default = _get_config_decimal(
            db, "costo_transporte_defecto", required=False, default=Decimal("0")
        )
        costo_cargue_default = _get_config_decimal(
            db, "costo_cargue_defecto", required=False, default=Decimal("0")
        )
        costo_descargue_default = _get_config_decimal(
            db, "costo_descargue_defecto", required=False, default=Decimal("0")
        )

        costo_transporte = costo_transporte_default
        costo_cargue = costo_cargue_default
        costo_descargue = costo_descargue_default
        costo_salvoconducto = total_m3 * tasa_salvoconducto

        valor_anticipo, total_monto = _calcular_valores_derivados(
            total_m3=total_m3,
            subtotal=subtotal,
            porcentaje_anticipo=porcentaje_anticipo,
            costo_transporte=costo_transporte,
            costo_cargue=costo_cargue,
            costo_descargue=costo_descargue,
            costo_salvoconducto=costo_salvoconducto,
        )

        fecha_emision = cotizacion.fecha_emision or datetime.utcnow()
        fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)

        cotizacion.total_m3 = total_m3
        cotizacion.subtotal = subtotal
        cotizacion.costo_transporte = costo_transporte
        cotizacion.costo_cargue = costo_cargue
        cotizacion.costo_descargue = costo_descargue
        cotizacion.costo_salvoconducto = costo_salvoconducto
        cotizacion.porcentaje_anticipo = porcentaje_anticipo
        cotizacion.valor_anticipo = valor_anticipo
        cotizacion.total_monto = total_monto
        cotizacion.fecha_vencimiento = fecha_vencimiento
        cotizacion.salvoconducto_es_manual = False
    else:
        if not update_data:
            raise HTTPException(status_code=400, detail="No data provided for update")

        if "salvoconducto_es_manual" in update_data:
            cotizacion.salvoconducto_es_manual = update_data.pop(
                "salvoconducto_es_manual"
            )

        cotizacion.sqlmodel_update(update_data)

        if any(
            key in update_data
            for key in [
                "costo_transporte",
                "costo_cargue",
                "costo_descargue",
                "costo_salvoconducto",
                "porcentaje_anticipo",
            ]
        ):
            valor_anticipo, total_monto = _calcular_valores_derivados(
                total_m3=cotizacion.total_m3,
                subtotal=cotizacion.subtotal,
                porcentaje_anticipo=cotizacion.porcentaje_anticipo,
                costo_transporte=cotizacion.costo_transporte,
                costo_cargue=cotizacion.costo_cargue,
                costo_descargue=cotizacion.costo_descargue,
                costo_salvoconducto=cotizacion.costo_salvoconducto,
            )
            cotizacion.valor_anticipo = valor_anticipo
            cotizacion.total_monto = total_monto

    db.add(cotizacion)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


@router.delete(
    "/{cotizacion_id}",
    status_code=204,
    dependencies=[Depends(require_permission(PermissionsEnum.DELETE_QUOTATION))],
)
async def eliminar_cotizacion(cotizacion_id: int, db: SessionDep):
    cotizacion = db.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(404, "Cotizacion no encontrada")
    db.delete(cotizacion)
    db.commit()
    return Response(status_code=204)
