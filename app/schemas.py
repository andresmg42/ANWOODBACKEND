from pydantic import BaseModel
from sqlmodel import SQLModel
from datetime import datetime
from decimal import Decimal


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserBase(SQLModel):
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


class TipoMaderaRelacion(SQLModel):
    id: int
    nombre: str


class MedidaRelacion(SQLModel):
    id: int
    ancho_mm: Decimal
    alto_mm: Decimal
    etiqueta: str | None = None


class PiezaPublic(PiezaCreate):
    id: int
    volumen_m3: Decimal
    estado: str
    fecha_ingreso: datetime
    created_at: datetime
    tipo_madera: TipoMaderaRelacion | None = None
    medida: MedidaRelacion | None = None


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
