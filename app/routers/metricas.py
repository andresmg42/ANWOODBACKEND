from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlmodel import select

from ..auth import PermissionsEnum, require_permission
from ..database import SessionDep
from ..models import (
    Cotizacion,
    DetalleCotizacion,
    EstadoCotizacionEnum,
    Role,
    TipoMadera,
    User,
    WoodPiece,
)
from ..schemas import DashboardMetrics

router = APIRouter(prefix="/metricas", tags=["metricas"])

ZERO = Decimal("0")


def _as_decimal(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _mes_label(fecha: datetime) -> str:
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return meses[fecha.month - 1]


def _next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1)
    return dt.replace(month=dt.month + 1)


@router.get(
    "/dashboard",
    response_model=DashboardMetrics,
    summary="Métricas del dashboard",
    dependencies=[Depends(require_permission(PermissionsEnum.GESTIONAR_INVENTARIO))],
)
async def dashboard(db: SessionDep):
    ahora = datetime.utcnow()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)

    cotizaciones_mes = db.exec(
        select(Cotizacion).where(
            Cotizacion.created_at >= inicio_mes,
            Cotizacion.estado == EstadoCotizacionEnum.APROBADA.value,
        )
    ).all()
    ventas_mes = sum((_as_decimal(c.total_monto) for c in cotizaciones_mes), ZERO)

    cotizaciones_mes_ant = db.exec(
        select(Cotizacion).where(
            Cotizacion.created_at >= inicio_mes_anterior,
            Cotizacion.created_at < inicio_mes,
            Cotizacion.estado == EstadoCotizacionEnum.APROBADA.value,
        )
    ).all()
    ventas_mes_anterior = sum(
        (_as_decimal(c.total_monto) for c in cotizaciones_mes_ant), ZERO
    )
    todas_cotizaciones_mes = db.exec(
        select(Cotizacion).where(Cotizacion.created_at >= inicio_mes)
    ).all()
    cot_pendientes = sum(
        1 for c in todas_cotizaciones_mes
        if c.estado == EstadoCotizacionEnum.BORRADOR.value
    )
    cot_aprobadas = sum(
        1 for c in todas_cotizaciones_mes
        if c.estado == EstadoCotizacionEnum.APROBADA.value
    )
    cot_rechazadas = sum(
        1 for c in todas_cotizaciones_mes
        if c.estado == EstadoCotizacionEnum.RECHAZADA.value
    )

    piezas = db.exec(
        select(WoodPiece).where(WoodPiece.estado == "disponible")
    ).all()
    productos_total = len(piezas)
    productos_stock_bajo = sum(
        1 for p in piezas if (p.cantidad - p.cantidad_reservada) <= 0
    )

    todos_usuarios = db.exec(select(User)).all()

    rol_cliente = db.exec(select(Role).where(Role.name == "user")).first()
    rol_cliente_id = rol_cliente.id if rol_cliente else None

    clientes = [
        u for u in todos_usuarios
        if u.role_id == rol_cliente_id and not u.disabled
    ]
    clientes_total = len(clientes)


    usuarios_activos = sum(
        1 for u in todos_usuarios
        if not u.disabled and u.role_id != rol_cliente_id
    )

    clientes_nuevos_mes = sum(
        1 for u in clientes
        if getattr(u, "created_at", None) and u.created_at >= inicio_mes
    )

    # ── Series mensuales ─────────────────────────────────────────────────────
    ventas_mensuales = []
    cotizaciones_mensuales = []
    clientes_mensuales = []

    for i in range(5, -1, -1):
        target = ahora - timedelta(days=30 * i)
        inicio = target.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin = _next_month(inicio)
        label = _mes_label(inicio)

        cots_aprobadas_mes = db.exec(
            select(Cotizacion).where(
                Cotizacion.created_at >= inicio,
                Cotizacion.created_at < fin,
                Cotizacion.estado == EstadoCotizacionEnum.APROBADA.value,
            )
        ).all()
        total_mes = float(
            sum((_as_decimal(c.total_monto) for c in cots_aprobadas_mes), ZERO)
        )
        ventas_mensuales.append({"mes": label, "ventas": total_mes})

        cots_mes = db.exec(
            select(Cotizacion).where(
                Cotizacion.created_at >= inicio,
                Cotizacion.created_at < fin,
            )
        ).all()
        cotizaciones_mensuales.append({
            "mes": label,
            "aprobadas": sum(
                1 for c in cots_mes
                if c.estado == EstadoCotizacionEnum.APROBADA.value
            ),
            "rechazadas": sum(
                1 for c in cots_mes
                if c.estado == EstadoCotizacionEnum.RECHAZADA.value
            ),
            "pendientes": sum(
                1 for c in cots_mes
                if c.estado == EstadoCotizacionEnum.BORRADOR.value
            ),
        })

        nuevos = sum(
            1 for u in clientes
            if getattr(u, "created_at", None) and inicio <= u.created_at < fin
        )
        clientes_mensuales.append({"mes": label, "nuevos": nuevos})

    # ── Top productos (últimos 6 meses) ──────────────────────────────────────
    seis_meses_atras = ahora - timedelta(days=180)
    ids_recientes = {
        c.id for c in db.exec(
            select(Cotizacion).where(Cotizacion.created_at >= seis_meses_atras)
        ).all()
    }

    detalles = db.exec(select(DetalleCotizacion)).all()
    conteo_tipos: dict[int, int] = {}
    for d in detalles:
        if d.cotizacion_id not in ids_recientes:
            continue
        pieza = db.get(WoodPiece, d.pieza_id)
        if pieza and pieza.tipo_madera_id:
            tid = pieza.tipo_madera_id
            conteo_tipos[tid] = conteo_tipos.get(tid, 0) + 1

    top_ids = sorted(conteo_tipos, key=lambda k: conteo_tipos[k], reverse=True)[:5]
    top_productos = []
    for tid in top_ids:
        tipo = db.get(TipoMadera, tid)
        if tipo:
            top_productos.append({
                "nombre": tipo.nombre,
                "cotizaciones": conteo_tipos[tid],
            })

    return {
        "ventas_mes": float(ventas_mes),
        "ventas_mes_anterior": float(ventas_mes_anterior),
        "cotizaciones_pendientes": cot_pendientes,
        "cotizaciones_aprobadas": cot_aprobadas,
        "cotizaciones_rechazadas": cot_rechazadas,
        "productos_total": productos_total,
        "productos_stock_bajo": productos_stock_bajo,
        "clientes_total": clientes_total,
        "clientes_nuevos_mes": clientes_nuevos_mes,
        "usuarios_activos": usuarios_activos,
        "ventas_mensuales": ventas_mensuales,
        "cotizaciones_mensuales": cotizaciones_mensuales,
        "clientes_mensuales": clientes_mensuales,
        "top_productos": top_productos,
    }