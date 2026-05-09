from pydantic import BaseModel
from sqlmodel import Enum, SQLModel, Field
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None

class UserBase(SQLModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    

class UserPublic(UserBase):
    id:int
    
    
    
class UserIn(UserBase):
    password:str
    

class UserInDB(UserBase):
    hashed_password: str
    disabled: bool | None = None


class ProductCreate(SQLModel):
    name: str
    code: str
    price: float
    cost_price:float
    stock_quantity: int
    description: str | None = None
    

class ProductPublic(SQLModel):
    id:int
    name:str
    code: str
    price:float
    stock_quantity:int
    description:str | None
    

class ProductUpdate(SQLModel):
    name: str | None = None
    code: str
    price: float | None = None
    stock_quantity: int | None = None
    description: str | None = None
    is_active: bool | None = None

class SalesCreate(SQLModel):
    total_price:float
    product_ids:list[int]

class CreateSale(SQLModel):
    items: list["SaleItemCreate"]

class SaleItemCreate(SQLModel):
    product_id:int
    unit_price:float
    quantity:int

class SaleItemPublic(SQLModel):
    product_id:int
    unit_price:float
    quantity:int

class SalePublic(SQLModel):
    id:int
    user_id:int
    created_at:datetime
    total_price:float
    items: list[SaleItemPublic]
