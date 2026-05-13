from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Token(BaseModel):
    access_token: str
    token_type: str


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
    name: str | None = None


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
    costo_total: Decimal | None = None


class LotePublic(LoteCreate):
    id: int
    estado: str
    fecha_ingreso: datetime
    created_at: datetime


class CategoriaBase(SQLModel):
    nombre: str
    estrategia_precio: str
    permite_cubicacion: bool = True
    formula_cubicacion: str = "largo_x_alto_x_ancho_div_10"
    min_precio_m3: Decimal | None = None
    max_precio_m3: Decimal | None = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(SQLModel):
    nombre: str | None = None
    estrategia_precio: str | None = None
    permite_cubicacion: bool | None = None
    formula_cubicacion: str | None = None
    min_precio_m3: Decimal | None = None
    max_precio_m3: Decimal | None = None


class CategoriaPublic(CategoriaBase):
    id: int


class TipoMaderaBase(SQLModel):
    categoria_id: int
    nombre: str
    densidad_kg_m3: Decimal
    precio_por_metro: Decimal
    descripcion: str | None = None
    activo: bool = True
    permite_cubicacion: bool = True
    imagenes: list[str] = Field(default_factory=list)


class TipoMaderaCreate(TipoMaderaBase):
    pass


class TipoMaderaUpdate(SQLModel):
    categoria_id: int | None = None
    nombre: str | None = None
    densidad_kg_m3: Decimal | None = None
    precio_por_metro: Decimal | None = None
    descripcion: str | None = None
    activo: bool | None = None
    permite_cubicacion: bool | None = None
    imagenes: list[str] | None = None


class TipoMaderaRelacion(SQLModel):
    id: int
    nombre: str


class CategoriaIn(SQLModel):
    nombre: str
    estrategia_precio: str
    permite_cubicacion: bool
    min_precio_m3: Decimal | None = None
    max_precio_m3: Decimal | None = None


class CategoriaPublic(SQLModel):
    id: int
    nombre: str
    estrategia_precio: str
    permite_cubicacion: bool
    min_precio_m3: Decimal | None = None
    max_precio_m3: Decimal | None = None


class TipoMaderaPublic(SQLModel):
    id: int
    nombre: str
    densidad_kg_m3: Decimal
    precio_por_metro: Decimal
    descripcion: str | None = None
    activo: bool
    permite_cubicacion: bool
    imagenes: list[str] = Field(default_factory=list)
    categoria: Optional[CategoriaPublic] = None


class MedidaBase(SQLModel):
    ancho_in: Decimal
    alto_in: Decimal
    etiqueta: str | None = None
    es_estandar: bool = True
    permite_cubicacion: bool = True
    precio_minimo_por_metro: Decimal | None = None


class MedidaCreate(MedidaBase):
    pass


class MedidaUpdate(SQLModel):
    ancho_in: Decimal | None = None
    alto_in: Decimal | None = None
    etiqueta: str | None = None
    es_estandar: bool | None = None
    permite_cubicacion: bool | None = None
    precio_minimo_por_metro: Decimal | None = None


class MedidaPublic(MedidaBase):
    id: int


class MedidaRelacion(SQLModel):
    id: int
    ancho_in: Decimal
    alto_in: Decimal
    etiqueta: str | None = None
    es_estandar: bool
    permite_cubicacion: bool


class PiezaCreate(SQLModel):
    tipo_madera_id: int
    medida_id: int
    lote_id: int | None = None
    largo_m: Decimal
    costo_unitario: Decimal | None = None
    precio_unitario: Decimal | None = None
    cantidad: int = 0


class PiezaPublic(SQLModel):
    id: int
    largo_m: Decimal | None = None
    volumen_m3: Decimal | None = None
    cantidad: int
    cantidad_reservada: int
    stock: int
    estado: str
    precio_unitario: Decimal | None = None
    costo_unitario: Decimal | None = None
    fecha_ingreso: datetime
    tipo_madera: Optional[TipoMaderaPublic] = None
    medida: Optional[MedidaPublic] = None


class PiezaUpdate(SQLModel):
    estado: str | None = None
    largo_m: Decimal | None = None
    precio_unitario: Decimal | None = None
    costo_unitario: Decimal | None = None


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


# ─── Cotizacion ─────────


class CotizacionBase(SQLModel):
    user_id: int
    numero_cotizacion: str | None = None
    estado: str | None = None
    tipo_compra: str | None = None
    costo_transporte: Decimal | None = None
    costo_cargue: Decimal | None = None
    costo_descargue: Decimal | None = None
    salvoconducto_es_manual: bool | None = False


class CotizacionCreate(CotizacionBase):
    pass


class CotizacionUpdate(SQLModel):
    estado: str | None = None
    tipo_compra: str | None = None
    costo_transporte: Decimal | None = None
    costo_cargue: Decimal | None = None
    costo_descargue: Decimal | None = None
    costo_salvoconducto: Decimal | None = None
    porcentaje_anticipo: Decimal | None = None
    salvoconducto_es_manual: bool | None = None
    fecha_vencimiento: datetime | None = None
    recalcular: bool | None = False


class CotizacionPublic(SQLModel):
    id: int
    user_id: int
    numero_cotizacion: str
    estado: str
    tipo_compra: str | None = None
    total_m3: Decimal
    subtotal: Decimal
    costo_transporte: Decimal
    costo_cargue: Decimal
    costo_descargue: Decimal
    costo_salvoconducto: Decimal
    porcentaje_anticipo: Decimal
    valor_anticipo: Decimal
    total_monto: Decimal
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
    volumen_unitario_m3: Decimal
    precio_unitario_snapshot: Decimal
    subtotal: Decimal


class DetalleCotizacionCreate(DetalleCotizacionBase):
    subtotal: Decimal | None = None


class DetalleCotizacionUpdate(SQLModel):
    descripcion_item: str | None = None
    cantidad: int | None = None
    volumen_unitario_m3: Decimal | None = None
    precio_unitario_snapshot: Decimal | None = None
    subtotal: Decimal | None = None


class DetalleCotizacionPublic(DetalleCotizacionBase):
    id: int
