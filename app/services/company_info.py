import os
from typing import Any

from sqlmodel import Session, select

from ..models import Configuration

POLICIES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "policies.txt")

COMPANY_PROFILE: dict[str, Any] = {
    "nombre": "ANGWOOD",
    "sector": "Venta de madera y derivados",
    "descripcion": (
        "ANGWOOD es una empresa especializada en la comercialización de madera "
        "corta y larga para construcción, estructuras y proyectos carpinteros."
    ),
    "categorias_producto": ["Madera Corta", "Madera Larga"],
    "servicios": [
        "Venta de madera por metro y por cubicación",
        "Cotizaciones con desglose de transporte, cargue y descargue",
        "Asesoría sobre tipos de madera según el proyecto",
        "Gestión de pedidos y carrito de compras",
    ],
    "moneda": "COP (pesos colombianos)",
    "contacto": {
        "telefono": "(+57) 315 622 40 81",
        "direccion": "Cl. 5a #79-93 a 79-1, Buenaventura, Valle del Cauca",
        "codigo_postal": "764501",
        "nota": "Para pedidos personalizados o visitas, contacta al equipo comercial de ANGWOOD.",
    },
}

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "horarios": ["horario", "hora", "abierto", "atencion", "atención"],
    "pagos": ["pago", "anticipo", "cotizacion", "cotización", "precio", "factura"],
    "envios": ["envio", "envío", "transporte", "salvoconducto", "entrega", "despacho"],
    "empresa": ["empresa", "quienes", "quiénes", "angwood", "informacion", "información"],
    "politicas": ["politica", "política", "descuento", "minimo", "mínimo", "lote", "restriccion"],
}


def load_business_policies() -> str | None:
    try:
        with open(POLICIES_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def get_company_info(db: Session, tema: str | None = None) -> dict[str, Any]:
    configs = db.exec(select(Configuration)).all()
    config_map = {c.clave: c.valor for c in configs}

    policies = load_business_policies()
    info: dict[str, Any] = {
        **COMPANY_PROFILE,
        "politicas_comerciales": {
            "porcentaje_anticipo": config_map.get("porcentaje_anticipo"),
            "dias_vencimiento_cotizacion": config_map.get("dias_vencimiento_cotizacion"),
            "tasa_salvoconducto_por_m3": config_map.get("tasa_salvoconducto_por_m3"),
            "costo_transporte_defecto": config_map.get("costo_transporte_defecto"),
            "costo_cargue_defecto": config_map.get("costo_cargue_defecto"),
            "costo_descargue_defecto": config_map.get("costo_descargue_defecto"),
        },
    }
    if policies:
        info["politicas_negocio_detalladas"] = policies

    if tema and tema.strip():
        term = tema.strip().lower()
        matched = [
            key for key, words in TOPIC_KEYWORDS.items() if any(w in term for w in words)
        ]
        if matched:
            info["tema_solicitado"] = tema
            info["temas_relevantes"] = matched

    return info
