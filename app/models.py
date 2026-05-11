from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from decimal import Decimal
from typing import Optional


class RolePermissions(SQLModel, table=True):
    role_id: int = Field(primary_key=True, foreign_key="role.id", default=None)
    permission_id: int = Field(
        primary_key=True, foreign_key="permission.id", default=None
    )


class Role(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None, index=True)
    permissions: list["Permission"] = Relationship(
        back_populates="roles", link_model=RolePermissions
    )
    users: list["User"] = Relationship(back_populates="role")


class Permission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(unique=True)
    roles: list["Role"] = Relationship(
        back_populates="permissions", link_model=RolePermissions
    )


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    username: str = Field(default=None, index=True, unique=True)
    email: str | None = Field(default=None)
    full_name: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    disabled: bool | None = Field(default=False)
    role_id: int | None = Field(foreign_key="role.id", default=None)
    hashed_password: str
    role: Optional["Role"] = Relationship(back_populates="users")
    cart: Optional["Cart"] = Relationship(back_populates="user")
    movimientos: list["MovimientoInventario"] = Relationship(back_populates="usuario")


class Cart(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(default=None, foreign_key="user.id", unique=True)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
    user: Optional["User"] = Relationship(back_populates="cart")
    items: list["ItemCart"] = Relationship(back_populates="cart")


class LoteInventory(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    codigo_lote: str | None = Field(default=None, unique=True, index=True)
    proveedor: str | None = Field(default=None)
    fecha_ingreso: datetime | None = Field(default_factory=datetime.utcnow)
    costo_total: Decimal | None = Field(default=None)
    estado: str | None = Field(default="activo")
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    piezas: list["WoodPiece"] = Relationship(back_populates="lote")

class Categoria(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    nombre: str = Field(index=True)
    estrategia_precio: str
    permite_cubicacion: bool = Field(default=True)
    min_precio_m3: Decimal
    max_precio_m3: Decimal
    
    tipos_madera: list["TipoMadera"] = Relationship(back_populates="categoria")

class TipoMadera(SQLModel, table=True):
    __tablename__ = "tipo_madera"
    id: int | None = Field(primary_key=True, default=None)

    categoria_id: int = Field(foreign_key="categoria.id")
    nombre: str = Field(index=True)
    densidad_kg_m3: Decimal
    precio_por_metro: Decimal
    descripcion: Optional[str] = None
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    categoria: Optional[Categoria] = Relationship(back_populates="tipos_madera")
    piezas: list["WoodPiece"] = Relationship(back_populates="tipo_madera")
    

class Medida(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    ancho_mm: float
    alto_mm: float
    etiqueta: str | None = None
    piezas: list["WoodPiece"] = Relationship(back_populates="medida")

class WoodPiece(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)

    tipo_madera_id: int | None = Field(default=None, foreign_key="tipo_madera.id")
    medida_id: int | None = Field(default=None, foreign_key="medida.id")

    lote_id: int | None = Field(default=None, foreign_key="loteinventory.id")
    largo_mm: int | None = Field(default=None)
    volumen_m3: Decimal | None = Field(default=None)
    cantidad: int = Field(default=0)
    cantidad_reservada: int = Field(default=0)
    stock: int | None = Field(default=None, exclude=True)
    estado: str | None = Field(default="disponible")
    costo_unitario: Decimal | None = Field(default=None)
    precio_unitario: Decimal | None = Field(default=None)
    fecha_ingreso: datetime | None = Field(default_factory=datetime.utcnow)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    tipo_madera: Optional["TipoMadera"] = Relationship(back_populates="piezas")
    medida: Optional["Medida"] = Relationship(back_populates="piezas")

    lote: Optional["LoteInventory"] = Relationship(back_populates="piezas")
    items_carrito: list["ItemCart"] = Relationship(back_populates="pieza")
    movimientos: list["MovimientoInventario"] = Relationship(back_populates="pieza")
    # detalles_cotizacion: list["DetalleCotizacion"] = Relationship(back_populates="pieza")


class ItemCart(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    carrito_id: int | None = Field(default=None, foreign_key="cart.id")
    wood_piece_id: int | None = Field(default=None, foreign_key="woodpiece.id")
    cantidad: int | None = Field(default=1)
    added_at: datetime | None = Field(default_factory=datetime.utcnow)
    cart: Optional["Cart"] = Relationship(back_populates="items")
    pieza: Optional["WoodPiece"] = Relationship(back_populates="items_carrito")


class MovimientoInventario(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    pieza_id: int | None = Field(default=None, foreign_key="woodpiece.id")
    usuario_id: int | None = Field(default=None, foreign_key="user.id")
    tipo_movimiento: str | None = Field(default=None)
    cantidad: int | None = Field(default=1)
    referencia_id: int | None = Field(default=None)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)

    pieza: Optional["WoodPiece"] = Relationship(back_populates="movimientos")
    usuario: Optional["User"] = Relationship(back_populates="movimientos")
