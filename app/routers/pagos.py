from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import uuid4

import mercadopago
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import select

from ..auth import RoleEnum, get_current_active_user
from ..database import SessionDep
from ..models import Cart, Cotizacion, DetalleCotizacion, EstadoCotizacionEnum, ItemCart, Pago, User, WoodPiece
from ..schemas import PagoCreate, PagoPublic, PagoPublicWithUser, PreferenciaResponse

load_dotenv()

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
APP_URL = os.getenv("APP_URL", "http://localhost:3000")
API_URL = os.getenv("API_URL", "http://localhost:8000")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

router = APIRouter(tags=["Pagos"])

FINAL_STATUSES = {"approved", "rejected", "cancelled"}


def require_admin_or_staff(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if not current_user.role or current_user.role.name not in {
        RoleEnum.ADMIN.value,
        RoleEnum.STAFF.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol admin o staff",
        )
    return current_user


def _map_mp_status(mp_status: str | None) -> str:
    if not mp_status:
        return "pending"
    if mp_status == "approved":
        return "approved"
    if mp_status in {"rejected", "charged_back"}:
        return "rejected"
    if mp_status in {"cancelled", "refunded"}:
        return "cancelled"
    return "pending"


def _vaciar_carrito_usuario(user_id: int, db: SessionDep) -> None:
    carrito = db.exec(select(Cart).where(Cart.user_id == user_id)).first()
    if not carrito:
        return

    for item in carrito.items[:]:
        pieza = db.get(WoodPiece, item.wood_piece_id)
        if pieza:
            pieza.cantidad_reservada -= item.cantidad
        db.delete(item)

    carrito.updated_at = datetime.utcnow()


def _crear_cotizacion_desde_pago(pago: Pago, db: SessionDep) -> None:
    """Reduce stock y genera una Cotizacion aprobada a partir de un Pago confirmado."""
    items: list[dict] = pago.items_json if isinstance(pago.items_json, list) else []
    if not items:
        return

    total_m3 = Decimal("0")
    subtotal = Decimal("0")
    detalles_data: list[dict] = []

    for item in items:
        pieza_id = item.get("pieza_id")
        cantidad = int(item.get("cantidad") or 0)
        precio_unitario = Decimal(str(item.get("precio_unitario") or 0))
        titulo = item.get("titulo") or f"Pieza {pieza_id}"

        pieza = db.get(WoodPiece, pieza_id) if pieza_id else None
        volumen_unitario = (
            Decimal(str(pieza.volumen_m3)) if pieza and pieza.volumen_m3 else Decimal("0")
        )

        if pieza and cantidad > 0:
            pieza.cantidad = max(0, pieza.cantidad - cantidad)
            db.add(pieza)

        item_subtotal = precio_unitario * Decimal(str(cantidad))
        total_m3 += volumen_unitario * Decimal(str(cantidad))
        subtotal += item_subtotal

        if pieza_id is not None:
            detalles_data.append(
                {
                    "pieza_id": pieza_id,
                    "descripcion_item": titulo,
                    "cantidad": cantidad,
                    "volumen_unitario_m3": volumen_unitario,
                    "precio_unitario_snapshot": precio_unitario,
                    "subtotal": item_subtotal,
                }
            )

    ahora = datetime.utcnow()
    numero = f"VENTA-{ahora.year}-{str(uuid4())[:8].upper()}"

    cotizacion = Cotizacion(
        user_id=pago.user_id,
        numero_cotizacion=numero,
        estado=EstadoCotizacionEnum.APROBADA.value,
        via_transporte="tierra",
        total_m3=total_m3,
        subtotal=subtotal,
        costo_transporte=Decimal("0"),
        costo_cargue=Decimal("0"),
        costo_descargue=Decimal("0"),
        costo_salvoconducto=Decimal("0"),
        porcentaje_anticipo=Decimal("0"),
        valor_anticipo=Decimal("0"),
        total_monto=pago.monto_total,
        fecha_emision=ahora,
    )
    db.add(cotizacion)
    db.flush()

    for d in detalles_data:
        db.add(DetalleCotizacion(cotizacion_id=cotizacion.id, **d))


def _extract_payment_id(payload: dict[str, Any]) -> str | None:
    if payload.get("type") == "payment" or payload.get("topic") == "payment":
        data = payload.get("data") or {}
        payment_id = data.get("id") or payload.get("id")
        if payment_id is not None:
            return str(payment_id)
    return None


@router.post(
    "/preferencia",
    response_model=PreferenciaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear preferencia de pago en Mercado Pago",
)
async def crear_preferencia(
    data: PagoCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe incluir al menos un item",
        )

    mp_items = []
    monto_total = Decimal("0")
    items_json: list[dict[str, Any]] = []

    for item in data.items:
        if item.cantidad <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cantidad debe ser mayor a 0",
            )
        subtotal = Decimal(str(item.precio_unitario)) * item.cantidad
        monto_total += subtotal
        mp_items.append(
            {
                "title": item.titulo,
                "quantity": item.cantidad,
                "unit_price": float(item.precio_unitario),
                "currency_id": "COP",
            }
        )
        items_json.append(
            {
                "pieza_id": item.pieza_id,
                "titulo": item.titulo,
                "cantidad": item.cantidad,
                "precio_unitario": float(item.precio_unitario),
            }
        )

    is_local = APP_URL.startswith("http://localhost") or APP_URL.startswith("http://127")

    preference_payload = {
        "items": mp_items,
        "payer": {
            "name": data.payer.name,
            "email": data.payer.email,
        },
        "back_urls": {
            "success": f"{APP_URL}/?pago=exitoso",
            "failure": f"{APP_URL}/?pago=fallido",
            "pending": f"{APP_URL}/?pago=pendiente",
        },
        "metadata": {"user_id": current_user.id},
    }

    # MP rechaza auto_return y notification_url cuando las URLs apuntan a localhost
    if not is_local:
        preference_payload["auto_return"] = "approved"
        preference_payload["notification_url"] = f"{API_URL}/pagos/webhook"

    print(f"[crear_preferencia] Enviando payload a MP: {preference_payload}")
    try:
        preference_response = sdk.preference().create(preference_payload)
    except Exception as e:
        print(f"[crear_preferencia] Excepción al llamar al SDK de MP: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al conectar con Mercado Pago",
        )

    print(f"[crear_preferencia] Respuesta de MP - status: {preference_response.get('status')}, response: {preference_response.get('response')}")

    if preference_response.get("status") not in {200, 201}:
        print(f"[crear_preferencia] Error de MP - respuesta completa: {preference_response}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al crear preferencia en Mercado Pago",
        )

    preference = preference_response["response"]
    preference_id = preference["id"]
    init_point = preference.get("init_point", "")
    sandbox_init_point = preference.get("sandbox_init_point", init_point)

    pago = Pago(
        user_id=current_user.id,
        preference_id=preference_id,
        status="pending",
        monto_total=monto_total,
        items_json=items_json,
    )
    db.add(pago)
    try:
        db.commit()
    except Exception as e:
        print(f"[crear_preferencia] Error al guardar pago en BD: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar el pago en la base de datos",
        )

    return PreferenciaResponse(
        preference_id=preference_id,
        init_point=init_point,
        sandbox_init_point=sandbox_init_point,
        payment_url=sandbox_init_point,
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Webhook IPN de Mercado Pago",
)
async def webhook_pago(request: Request, db: SessionDep):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    query_params = dict(request.query_params)
    if not payload and query_params:
        payload = query_params

    payment_id = _extract_payment_id(payload)
    if not payment_id:
        return {"ok": True}

    payment_response = sdk.payment().get(payment_id)
    if payment_response.get("status") not in {200, 201}:
        return {"ok": True}

    payment = payment_response["response"]
    preference_id = payment.get("preference_id") or payment.get("metadata", {}).get(
        "preference_id"
    )
    if not preference_id:
        external_reference = payment.get("external_reference")
        if external_reference:
            pago = db.exec(
                select(Pago).where(Pago.preference_id == external_reference)
            ).first()
        else:
            user_id = payment.get("metadata", {}).get("user_id")
            if not user_id:
                return {"ok": True}
            pago = db.exec(
                select(Pago)
                .where(Pago.user_id == user_id)
                .where(Pago.status == "pending")
                .order_by(Pago.created_at.desc())
            ).first()
    else:
        pago = db.exec(select(Pago).where(Pago.preference_id == preference_id)).first()

    if not pago:
        return {"ok": True}

    new_status = _map_mp_status(payment.get("status"))
    mp_payment_id = str(payment.get("id", payment_id))

    if (
        pago.mp_payment_id == mp_payment_id
        and pago.status in FINAL_STATUSES
        and pago.status == new_status
    ):
        return {"ok": True}

    pago.mp_payment_id = mp_payment_id
    pago.status = new_status
    pago.updated_at = datetime.utcnow()
    db.add(pago)
    db.commit()

    if new_status == "approved":
        _crear_cotizacion_desde_pago(pago, db)
        _vaciar_carrito_usuario(pago.user_id, db)
        db.commit()

    return {"ok": True}


@router.get(
    "",
    response_model=list[PagoPublicWithUser],
    summary="Listar pagos (admin/staff)",
)
async def listar_pagos(
    current_user: Annotated[User, Depends(require_admin_or_staff)],
    db: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    pagos = db.exec(
        select(Pago).order_by(Pago.created_at.desc()).offset(skip).limit(limit)
    ).all()

    result: list[PagoPublicWithUser] = []
    for pago in pagos:
        user = db.get(User, pago.user_id)
        result.append(
            PagoPublicWithUser(
                payment_id=pago.id,
                preference_id=pago.preference_id,
                status=pago.status,
                monto_total=pago.monto_total,
                created_at=pago.created_at,
                mp_payment_id=pago.mp_payment_id,
                user_id=pago.user_id,
                username=user.username if user else None,
                email=user.email if user else None,
            )
        )
    return result


@router.get(
    "/{payment_id}",
    response_model=PagoPublic,
    summary="Consultar estado de un pago",
)
async def obtener_pago(
    payment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: SessionDep,
):
    pago = db.get(Pago, payment_id)
    if not pago:
        pago = db.exec(
            select(Pago).where(Pago.mp_payment_id == str(payment_id))
        ).first()
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    is_admin_or_staff = current_user.role and current_user.role.name in {
        RoleEnum.ADMIN.value,
        RoleEnum.STAFF.value,
    }
    if pago.user_id != current_user.id and not is_admin_or_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver este pago",
        )

    return PagoPublic(
        payment_id=pago.id,
        preference_id=pago.preference_id,
        status=pago.status,
        monto_total=pago.monto_total,
        created_at=pago.created_at,
        mp_payment_id=pago.mp_payment_id,
    )
