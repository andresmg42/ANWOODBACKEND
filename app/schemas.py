from pydantic import BaseModel
from sqlmodel import SQLModel
from datetime import datetime
from decimal import Decimal
from typing import Optional


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


class UserInDB(UserBase):
    hashed_password: str
    disabled: bool | None = None


class ChangeRole(BaseModel):
    name: str | None = None


# ─── Cart ───────────


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


# ─── LoteInventory ─────────


class LoteCreate(SQLModel):
    codigo_lote: str
    proveedor: str | None = None
    costo_total: Decimal | None = None


class LotePublic(LoteCreate):
    id: int
    estado: str
    fecha_ingreso: datetime
    created_at: datetime


# ─── WoodPiece ─────────────


class PiezaCreate(SQLModel):
    tipo_madera_id: int
    medida_id: int
    lote_id: int | None = None
    largo_mm: int
    costo_unitario: Decimal | None = None
    precio_unitario: Decimal | None = None
    cantidad: int = 0
    cantidad_reservada: int = 0


class TipoMaderaRelacion(SQLModel):
    id: int
    nombre: str

class CategoriaPublic(SQLModel):
    id: int
    nombre: str
    estrategia_precio: str
    permite_cubicacion: bool

class TipoMaderaPublic(SQLModel):
    id: int
    nombre: str
    densidad_kg_m3: Decimal
    precio_por_metro: Decimal
    categoria: Optional[CategoriaPublic] = None

class MedidaPublic(SQLModel):
    id: int
    ancho_mm: float
    alto_mm: float


class MedidaRelacion(SQLModel):
    id: int
    ancho_mm: Decimal
    alto_mm: Decimal
    etiqueta: str | None = None

class PiezaPublic(SQLModel):
    id: int
    volumen_m3: Decimal
    cantidad: int
    cantidad_reservada: int
    stock: int 
    estado: str
    precio_unitario: Decimal | None = None
    costo_unitario: Decimal | None = None
    fecha_ingreso: datetime
    tipo_madera: Optional[TipoMaderaPublic] = None
    medida: Optional["MedidaPublic"] = None

class PiezaUpdate(SQLModel):
    estado: str | None = None
    precio_unitario: Decimal | None = None
    costo_unitario: Decimal | None = None


# ─── Movimiento ─────────────


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
