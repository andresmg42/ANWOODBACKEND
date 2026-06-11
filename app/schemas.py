from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .types import ApiDecimal


class Token(BaseModel):
    access_token: str = Field(description="JWT para usar en Authorization: Bearer")
    token_type: str = Field(default="bearer", description="Tipo de token (siempre bearer)")


class TokenData(BaseModel):
    username: str | None = None


class UserBase(SQLModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None


class UserPublic(UserBase):
    id: int


class UserIn(UserBase):
    password: str
    role_id: int | None = 3


class UserUpdate(SQLModel):
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    password: str | None = None
    role_id: int | None = None
    disabled: bool | None = False


class UserInDB(UserBase):
    hashed_password: str
    disabled: bool | None = None
    role_id: int | None = 3


class ChangeRole(BaseModel):
    name: str | None = Field(
        default=None,
        description="Nombre del rol: admin, staff o user.",
    )


class MessageResponse(BaseModel):
    message: str


class DetailResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    ok: bool


class ItemCartAdd(SQLModel):
    wood_piece_id: int
    cantidad: int = 1


class ItemCartPublic(SQLModel):
    id: int
    wood_piece_id: int
    cantidad: int
    added_at: datetime


class CartPublic(SQLModel):
    id: int
    user_id: int
    items: list["ItemCartPublic"] = []
    updated_at: datetime


class ItemCartUpdate(SQLModel):
    cantidad: int


class LoteCreate(SQLModel):
    codigo_lote: str
    proveedor: str | None = None
    costo_total: ApiDecimal | None = None
    fecha_ingreso: datetime | None = Field(
        default=None,
        description="Fecha de ingreso del lote. Si se omite, se usa la fecha actual.",
    )


class LotePublic(LoteCreate):
    id: int
    estado: str
    fecha_ingreso: datetime
    created_at: datetime


class CategoriaBase(SQLModel):
    nombre: str
    estrategia_precio: str
    formula_cubicacion: str = "largo_x_alto_x_ancho_div_10"
    min_precio_m3: ApiDecimal | None = None
    max_precio_m3: ApiDecimal | None = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(SQLModel):
    nombre: str | None = None
    estrategia_precio: str | None = None
    formula_cubicacion: str | None = None
    min_precio_m3: ApiDecimal | None = None
    max_precio_m3: ApiDecimal | None = None


class CategoriaPublic(CategoriaBase):
    id: int


class TipoMaderaBase(SQLModel):
    categoria_id: int
    nombre: str
    precio_por_metro: ApiDecimal
    descripcion: str | None = None
    activo: bool = True
    imagenes: list[str] = Field(default_factory=list)


class TipoMaderaCreate(TipoMaderaBase):
    pass


class TipoMaderaUpdate(SQLModel):
    categoria_id: int | None = None
    nombre: str | None = None
    precio_por_metro: ApiDecimal | None = None
    descripcion: str | None = None
    activo: bool | None = None
    imagenes: list[str] | None = None


class TipoMaderaRelacion(SQLModel):
    id: int
    nombre: str


class TipoMaderaPublic(SQLModel):
    id: int
    nombre: str
    precio_por_metro: ApiDecimal
    descripcion: str | None = None
    activo: bool
    imagenes: list[str] = Field(default_factory=list)
    categoria: Optional[CategoriaPublic] = None


class MedidaBase(SQLModel):
    ancho_in: ApiDecimal
    alto_in: ApiDecimal
    etiqueta: str | None = None
    es_estandar: bool = True
    cubica: bool = Field(
        default=True,
        description="Indica si la medida es cúbica (aplica cálculo por volumen).",
    )
    precio_minimo_por_metro: ApiDecimal | None = None


class MedidaCreate(MedidaBase):
    pass


class MedidaUpdate(SQLModel):
    ancho_in: ApiDecimal | None = None
    alto_in: ApiDecimal | None = None
    etiqueta: str | None = None
    es_estandar: bool | None = None
    cubica: bool | None = None
    precio_minimo_por_metro: ApiDecimal | None = None


class MedidaPublic(MedidaBase):
    id: int


class MedidaRelacion(SQLModel):
    id: int
    ancho_in: ApiDecimal
    alto_in: ApiDecimal
    etiqueta: str | None = None
    es_estandar: bool
    cubica: bool


class PiezaCreate(SQLModel):
    tipo_madera_id: int
    medida_id: int
    lote_id: int | None = None
    ancho_in: ApiDecimal | None = Field(
        default=None,
        description="Ancho en pulgadas. Si se omite, se copia de la medida.",
    )
    alto_in: ApiDecimal | None = Field(
        default=None,
        description="Alto en pulgadas. Si se omite, se copia de la medida.",
    )
    largo_m: ApiDecimal
    calidad: str | None = Field(
        default=None,
        description="Calidad de la pieza (ej. primera, segunda).",
    )
    costo_unitario: ApiDecimal | None = None
    precio_unitario: ApiDecimal | None = None
    cantidad: int = 0


class PiezaPublic(SQLModel):
    id: int
    ancho_in: ApiDecimal | None = None
    alto_in: ApiDecimal | None = None
    largo_m: ApiDecimal | None = None
    volumen_m3: ApiDecimal | None = None
    cantidad: int
    cantidad_reservada: int
    stock: int
    estado: str
    calidad: str | None = None
    precio_unitario: ApiDecimal | None = None
    costo_unitario: ApiDecimal | None = None
    created_at: datetime
    tipo_madera: Optional[TipoMaderaPublic] = None
    medida: Optional[MedidaPublic] = None


class PiezaUpdate(SQLModel):
    estado: str | None = None
    calidad: str | None = None
    ancho_in: ApiDecimal | None = None
    alto_in: ApiDecimal | None = None
    largo_m: ApiDecimal | None = None
    precio_unitario: ApiDecimal | None = None
    costo_unitario: ApiDecimal | None = None


class MovimientoInventarioPublic(SQLModel):
    id: int
    pieza_id: int
    usuario_id: int | None = None
    tipo_movimiento: str
    cantidad: int
    referencia_id: int | None = None
    created_at: datetime
    usuario_nombre: str | None = None
    pieza_info: dict | None = None


class ConfigurationBase(SQLModel):
    clave: str
    valor: str
    descripcion: str | None = None


class ConfigurationCreate(ConfigurationBase):
    pass


class ConfigurationUpdate(SQLModel):
    clave: str | None = None
    valor: str | None = None
    descripcion: str | None = None


class ConfigurationPublic(ConfigurationBase):
    id: int
    updated_at: datetime
    updated_by_id: int | None = None
    updated_by_nombre: str | None = None


# ─── Cotizacion ─────────


class CotizacionBase(SQLModel):
    user_id: int
    numero_cotizacion: str | None = None
    estado: str | None = None
    costo_transporte: ApiDecimal | None = None
    costo_cargue: ApiDecimal | None = None
    costo_descargue: ApiDecimal | None = None
    salvoconducto_es_manual: bool | None = False


class CotizacionCreate(CotizacionBase):
    pass


class CotizacionUpdate(SQLModel):
    estado: str | None = None
    costo_transporte: ApiDecimal | None = None
    costo_cargue: ApiDecimal | None = None
    costo_descargue: ApiDecimal | None = None
    costo_salvoconducto: ApiDecimal | None = None
    porcentaje_anticipo: ApiDecimal | None = None
    salvoconducto_es_manual: bool | None = None
    fecha_vencimiento: datetime | None = None
    recalcular: bool | None = False


class CotizacionPublic(SQLModel):
    id: int
    user_id: int
    numero_cotizacion: str
    estado: str
    total_m3: ApiDecimal
    subtotal: ApiDecimal
    costo_transporte: ApiDecimal
    costo_cargue: ApiDecimal
    costo_descargue: ApiDecimal
    costo_salvoconducto: ApiDecimal
    porcentaje_anticipo: ApiDecimal
    valor_anticipo: ApiDecimal
    total_monto: ApiDecimal
    fecha_emision: datetime
    fecha_vencimiento: datetime | None = None
    salvoconducto_es_manual: bool
    created_at: datetime


# ─── Detalle Cotizacion ─────────


class DetalleCotizacionBase(SQLModel):
    cotizacion_id: int
    pieza_id: int
    descripcion_item: str | None = None
    cantidad: int
    volumen_unitario_m3: ApiDecimal
    precio_unitario_snapshot: ApiDecimal
    subtotal: ApiDecimal


class DetalleCotizacionCreate(DetalleCotizacionBase):
    subtotal: ApiDecimal | None = None


class DetalleCotizacionUpdate(SQLModel):
    descripcion_item: str | None = None
    cantidad: int | None = None
    volumen_unitario_m3: ApiDecimal | None = None
    precio_unitario_snapshot: ApiDecimal | None = None
    subtotal: ApiDecimal | None = None


class DetalleCotizacionPublic(DetalleCotizacionBase):
    id: int


class MesVentas(BaseModel):
    mes: str
    ventas: float


class MesCotizaciones(BaseModel):
    mes: str
    aprobadas: int
    rechazadas: int
    pendientes: int


class MesClientes(BaseModel):
    mes: str
    nuevos: int


class TopProducto(BaseModel):
    nombre: str
    cotizaciones: int


class DashboardMetrics(BaseModel):
    ventas_mes: float
    ventas_mes_anterior: float
    cotizaciones_pendientes: int
    cotizaciones_aprobadas: int
    cotizaciones_rechazadas: int
    productos_total: int
    productos_stock_bajo: int
    clientes_total: int
    clientes_nuevos_mes: int
    usuarios_activos: int
    ventas_mensuales: list[MesVentas]
    cotizaciones_mensuales: list[MesCotizaciones]
    clientes_mensuales: list[MesClientes]
    top_productos: list[TopProducto]
