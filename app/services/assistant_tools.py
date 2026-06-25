FUNCTION_DECLARATIONS = [
    {
        "name": "informacion_empresa",
        "description": (
            "Información general de ANGWOOD: servicios, políticas comerciales, "
            "anticipos, transporte y datos de la empresa."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tema": {
                    "type": "string",
                    "description": (
                        "Tema específico: horarios, pagos, envios, empresa, politicas. Opcional."
                    ),
                },
            },
        },
    },
    {
        "name": "consultar_catalogo",
        "description": (
            "Consulta el catálogo de tipos de madera con precios y categorías."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_madera": {
                    "type": "string",
                    "description": "Nombre o fragmento del tipo de madera (ej. cedro).",
                },
                "categoria": {
                    "type": "string",
                    "description": "Filtrar por categoría: Madera Corta o Madera Larga.",
                },
            },
        },
    },
    {
        "name": "consultar_medidas",
        "description": "Lista medidas estándar disponibles (2x5, 3x6, 2x8, etc.).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_inventario",
        "description": (
            "Consulta inventario y disponibilidad de piezas con stock, medidas y precios."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_madera": {"type": "string", "description": "Tipo de madera."},
                "tipo_madera_id": {"type": "integer", "description": "ID del tipo."},
                "solo_con_stock": {
                    "type": "boolean",
                    "description": "Si true, solo piezas con unidades disponibles.",
                },
            },
        },
    },
    {
        "name": "consultar_cotizaciones",
        "description": (
            "Lista o consulta cotizaciones del usuario autenticado. "
            "Requiere sesión iniciada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "numero_cotizacion": {
                    "type": "string",
                    "description": "Número de cotización específico (ej. COT-2026-...).",
                },
                "cotizacion_id": {"type": "integer", "description": "ID de cotización."},
            },
        },
    },
    {
        "name": "generar_cotizacion",
        "description": (
            "Genera una cotización desde el carrito del usuario. "
            "Requiere sesión y carrito con items."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "via_transporte": {
                    "type": "string",
                    "description": (
                        "Vía de transporte para calcular costos: 'tierra' o 'mar'. "
                        "Default: tierra."
                    ),
                    "enum": ["tierra", "mar"],
                },
            },
        },
    },
    {
        "name": "consultar_carrito",
        "description": "Muestra el carrito de compras del usuario. Requiere sesión.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "agregar_al_carrito",
        "description": (
            "Agrega una pieza al carrito. Requiere sesión. "
            "Usar pieza_id o nombre_madera."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pieza_id": {"type": "integer", "description": "ID de la pieza."},
                "nombre_madera": {
                    "type": "string",
                    "description": "Tipo de madera si no se conoce el pieza_id.",
                },
                "cantidad": {
                    "type": "integer",
                    "description": "Cantidad a agregar (default 1).",
                },
            },
        },
    },
    {
        "name": "eliminar_del_carrito",
        "description": "Elimina un item del carrito por su item_id. Requiere sesión.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {"type": "integer", "description": "ID del item en el carrito."},
            },
            "required": ["item_id"],
        },
    },
    {
        "name": "vaciar_carrito",
        "description": "Vacía el carrito del usuario. Requiere sesión.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "recomendar_productos",
        "description": (
            "Recomienda tipos de madera según el proyecto, presupuesto o uso. "
            "Asesoría de productos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "proposito": {
                    "type": "string",
                    "description": (
                        "Uso previsto: construccion, estructura, muebles, exterior, economico."
                    ),
                },
                "presupuesto_max_por_metro": {
                    "type": "number",
                    "description": "Presupuesto máximo por metro en COP.",
                },
                "categoria": {
                    "type": "string",
                    "description": "Madera Corta o Madera Larga.",
                },
            },
        },
    },
]

FUNCTION_TO_CAPABILITY: dict[str, str] = {
    "informacion_empresa": "atencion_informacion",
    "consultar_catalogo": "consulta_catalogo",
    "consultar_medidas": "consulta_catalogo",
    "consultar_inventario": "consulta_inventario",
    "consultar_cotizaciones": "cotizaciones",
    "generar_cotizacion": "cotizaciones",
    "consultar_carrito": "carrito_pedidos",
    "agregar_al_carrito": "carrito_pedidos",
    "eliminar_del_carrito": "carrito_pedidos",
    "vaciar_carrito": "carrito_pedidos",
    "recomendar_productos": "recomendaciones",
}

SYSTEM_PROMPT = """Eres el asistente de voz de ANGWOOD, empresa de venta de madera en Colombia.

Debes cubrir estas 6 áreas de atención:

1. ATENCIÓN E INFORMACIÓN GENERAL — horarios, servicios, políticas, anticipos, transporte.
   Herramienta: informacion_empresa (incluye políticas comerciales detalladas del negocio)

2. CONSULTA DE CATÁLOGO — tipos de madera, precios, categorías y medidas.
   Herramientas: consultar_catalogo, consultar_medidas

3. CONSULTA DE INVENTARIO Y DISPONIBILIDAD — stock real de piezas.
   Herramienta: consultar_inventario

4. GENERACIÓN Y SEGUIMIENTO DE COTIZACIONES — listar y crear cotizaciones.
   Herramientas: consultar_cotizaciones, generar_cotizacion
   (requieren usuario autenticado)

5. GESTIÓN DE CARRITO Y PEDIDOS — ver, agregar, eliminar items del carrito.
   Herramientas: consultar_carrito, agregar_al_carrito, eliminar_del_carrito, vaciar_carrito
   (requieren usuario autenticado)

6. RECOMENDACIONES Y ASESORÍA — sugerir maderas según proyecto y presupuesto.
   Herramienta: recomendar_productos

Reglas:
- Responde siempre en español, claro y conciso (ideal para voz).
- Usa herramientas para datos reales; no inventes stock, precios ni cotizaciones.
- Si una operación requiere autenticación y el usuario no ha iniciado sesión, indícale
  que debe iniciar sesión en la app para gestionar carrito o cotizaciones.
- Precios en pesos colombianos (COP).
- Si no hay stock pero el producto está en catálogo, indícalo claramente.
- Para asesoría, combina recomendar_productos con datos de inventario cuando sea útil.
- Respeta las políticas comerciales (descuentos, mínimos de volumen, estados de piezas).
- Solo se venden piezas con estado 'disponible'; las 'reservadas' no están disponibles.
"""
