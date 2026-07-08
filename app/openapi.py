API_TITLE = "Angwood API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
Backend de gestión Angwood: inventario de madera, catálogo, carrito y cotizaciones.

### Autenticación
1. Obtén un token JWT en **POST /token** (`username` + `password`, form-urlencoded).
2. En endpoints protegidos usa el header: `Authorization: Bearer <token>`.
"""

OPENAPI_TAGS = [
    {"name": "auth", "description": "Login y tokens JWT."},
    {"name": "users", "description": "Usuarios, roles y permisos."},
    {"name": "health", "description": "Estado del servicio."},
    {"name": "cart", "description": "Carrito del usuario autenticado."},
    {"name": "inventory", "description": "Lotes y movimientos de inventario."},
    {"name": "proveedores", "description": "Proveedores de madera."},
    {"name": "pieza_madera", "description": "Piezas de madera en inventario."},
    {"name": "categorias", "description": "Categorías de producto."},
    {"name": "wood-types", "description": "Tipos de madera."},
    {"name": "medidas", "description": "Medidas estándar (ancho × alto en pulgadas)."},
    {"name": "configuracion", "description": "Parámetros globales del sistema."},
    {"name": "cotizaciones", "description": "Cotizaciones."},
    {"name": "detalle_cotizacion", "description": "Líneas de detalle de cotizaciones."},
    {"name": "metricas", "description": "Métricas del dashboard."},
    {"name": "Pagos", "description": "Pagos con Mercado Pago Checkout Pro."},
]
