from decimal import Decimal

from ..models import (
    Categoria,
    Cotizacion,
    DetalleCotizacion,
    FormulaCubicacionEnum,
    Medida,
    ReglaCalculoEnum,
    TipoMadera,
)
from .config_service import get_decimal_config


ZERO = Decimal("0")


def _as_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def resolver_precio_por_metro(medida: Medida, tipo_madera: TipoMadera) -> Decimal:
    precio_base = _as_decimal(tipo_madera.precio_por_metro)
    if not medida.es_estandar and medida.precio_minimo_por_metro is not None:
        return max(precio_base, _as_decimal(medida.precio_minimo_por_metro))
    return precio_base


def calcular_volumen(
    medida: Medida,
    largo_m: Decimal,
    categoria: Categoria,
    tipo_madera: TipoMadera,
    ancho_in: Decimal | None = None,
    alto_in: Decimal | None = None,
) -> Decimal:
    if not medida.permite_cubicacion:
        return ZERO
    if not categoria.permite_cubicacion:
        return ZERO
    if not tipo_madera.permite_cubicacion:
        return ZERO
    if (
        categoria.formula_cubicacion
        != FormulaCubicacionEnum.LARGO_X_ALTO_X_ANCHO_DIV_10.value
    ):
        return ZERO

    ancho = _as_decimal(ancho_in if ancho_in is not None else medida.ancho_in)
    alto = _as_decimal(alto_in if alto_in is not None else medida.alto_in)
    return (_as_decimal(largo_m) * alto * ancho) / Decimal("10")


def resolver_dimensiones_pieza(
    medida: Medida,
    ancho_in: Decimal | None = None,
    alto_in: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    return (
        _as_decimal(ancho_in if ancho_in is not None else medida.ancho_in),
        _as_decimal(alto_in if alto_in is not None else medida.alto_in),
    )


def calcular_detalle(detalle, medida: Medida, tipo_madera: TipoMadera, categoria: Categoria):
    largo_m = _as_decimal(detalle.largo_m)
    cantidad = detalle.cantidad
    precio_por_metro_aplicado = resolver_precio_por_metro(medida, tipo_madera)
    volumen_m3 = calcular_volumen(medida, largo_m, categoria, tipo_madera)

    if volumen_m3 > ZERO:
        regla = ReglaCalculoEnum.CUBICACION.value
        precio_unitario = volumen_m3 * precio_por_metro_aplicado
    else:
        regla = ReglaCalculoEnum.POR_LARGO.value
        precio_unitario = largo_m * precio_por_metro_aplicado

    subtotal = precio_unitario * Decimal(cantidad)
    return {
        "volumen_m3": volumen_m3,
        "precio_por_metro_aplicado": precio_por_metro_aplicado,
        "precio_unitario": precio_unitario,
        "subtotal": subtotal,
        "regla_calculo": regla,
    }


def construir_detalle_cotizacion(
    cotizacion_id: int,
    detalle_in,
    medida: Medida,
    tipo_madera: TipoMadera,
    categoria: Categoria,
) -> DetalleCotizacion:
    calculo = calcular_detalle(detalle_in, medida, tipo_madera, categoria)
    return DetalleCotizacion(
        cotizacion_id=cotizacion_id,
        tipo_madera_id=detalle_in.tipo_madera_id,
        medida_id=detalle_in.medida_id,
        wood_piece_id=detalle_in.wood_piece_id,
        largo_m=_as_decimal(detalle_in.largo_m),
        cantidad=detalle_in.cantidad,
        notas=detalle_in.notas,
        **calculo,
    )


def calcular_costos_adicionales(source, metros_totales: Decimal, db) -> dict:
    costo_cargue_terrestre = source.costo_cargue_terrestre
    if costo_cargue_terrestre is None:
        costo_cargue_terrestre = (
            metros_totales
            * get_decimal_config(db, "precio_cargue_terrestre_por_metro", ZERO)
        )

    costo_descargue_terrestre = source.costo_descargue_terrestre
    if costo_descargue_terrestre is None:
        costo_descargue_terrestre = (
            metros_totales
            * get_decimal_config(db, "precio_descargue_terrestre_por_metro", ZERO)
        )

    costo_cargue_maritimo = source.costo_cargue_maritimo
    if costo_cargue_maritimo is None:
        costo_cargue_maritimo = (
            metros_totales
            * get_decimal_config(db, "precio_cargue_maritimo_por_metro", ZERO)
        )

    costo_descargue_maritimo = source.costo_descargue_maritimo
    if costo_descargue_maritimo is None:
        costo_descargue_maritimo = (
            metros_totales
            * get_decimal_config(db, "precio_descargue_maritimo_por_metro", ZERO)
        )

    precio_epa_por_metro_usado = source.precio_epa_por_metro
    if precio_epa_por_metro_usado is None:
        precio_epa_por_metro_usado = get_decimal_config(
            db, "precio_epa_por_metro", Decimal("1500")
        )

    costo_salvoconducto_epa = metros_totales * _as_decimal(precio_epa_por_metro_usado)

    return {
        "costo_cargue_terrestre": _as_decimal(costo_cargue_terrestre),
        "costo_descargue_terrestre": _as_decimal(costo_descargue_terrestre),
        "costo_cargue_maritimo": _as_decimal(costo_cargue_maritimo),
        "costo_descargue_maritimo": _as_decimal(costo_descargue_maritimo),
        "precio_epa_por_metro_usado": _as_decimal(precio_epa_por_metro_usado),
        "costo_salvoconducto_epa": _as_decimal(costo_salvoconducto_epa),
    }


def recalcular_cotizacion(
    cotizacion: Cotizacion,
    detalles: list[DetalleCotizacion],
    db,
    cost_source=None,
):
    subtotal_piezas = sum((_as_decimal(detalle.subtotal) for detalle in detalles), ZERO)
    metros_totales = sum(
        (_as_decimal(detalle.largo_m) * Decimal(detalle.cantidad) for detalle in detalles),
        ZERO,
    )
    costos = calcular_costos_adicionales(cost_source or cotizacion, metros_totales, db)

    cotizacion.subtotal_piezas = subtotal_piezas
    cotizacion.metros_totales = metros_totales
    cotizacion.costo_cargue_terrestre = costos["costo_cargue_terrestre"]
    cotizacion.costo_descargue_terrestre = costos["costo_descargue_terrestre"]
    cotizacion.costo_cargue_maritimo = costos["costo_cargue_maritimo"]
    cotizacion.costo_descargue_maritimo = costos["costo_descargue_maritimo"]
    cotizacion.precio_epa_por_metro_usado = costos["precio_epa_por_metro_usado"]
    cotizacion.costo_salvoconducto_epa = costos["costo_salvoconducto_epa"]
    cotizacion.total = (
        cotizacion.subtotal_piezas
        + cotizacion.costo_cargue_terrestre
        + cotizacion.costo_descargue_terrestre
        + cotizacion.costo_cargue_maritimo
        + cotizacion.costo_descargue_maritimo
        + cotizacion.costo_salvoconducto_epa
    )
    cotizacion.monto_anticipo = (
        cotizacion.total * _as_decimal(cotizacion.porcentaje_anticipo)
    ) / Decimal("100")
    return cotizacion
