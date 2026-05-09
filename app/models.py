from sqlmodel import Field, SQLModel,Relationship
from datetime import datetime

class  RolePermissions(SQLModel,table=True):
    role_id:int = Field(primary_key=True,foreign_key="role.id",default=None)    
    permission_id:int = Field(primary_key=True,foreign_key="permission.id",default=None) 


class Role(SQLModel,table=True):
    id: int | None = Field(primary_key=True,default=None)
    name: str | None = Field(default=None,index=True)
    permissions: list["Permission"] = Relationship(back_populates='roles',link_model=RolePermissions)      
    users: list["User"] = Relationship(back_populates="role")
 

class Permission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None =Field(unique=True)
    roles: list[Role] = Relationship(back_populates='permissions',link_model=RolePermissions)      

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True,index=True)
    username: str = Field(index=True,unique=True)
    email: str | None = Field(default=None)
    full_name: str | None = Field(default=None)
    disabled: bool | None = Field(default=False)
    role_id: int | None = Field(foreign_key='role.id',default=None) 
    role: Role | None = Relationship(back_populates='users')
    sales: list["Sale"]=Relationship(back_populates='user')
    hashed_password: str 

class Product(SQLModel,table=True):
    id:int | None = Field(default=None,primary_key=True)
    name: str | None = Field(default=None,index=True)
    code: str | None = Field(default=None,index=True)
    description: str | None = None
    price: float | None = Field(default=None)
    cost_price: float | None = Field(default=None)
    stock_quantity: int | None= Field(default=0,ge=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sale_items: list["SaleProducts"] = Relationship(back_populates='product')

class Sale(SQLModel,table=True):
    id:int | None = Field(default=None,primary_key=True)
    user_id:int | None = Field(default=None,foreign_key='user.id')
    user: User | None = Relationship(back_populates='sales')
    created_at: datetime= Field(default_factory=datetime.utcnow)
    total_price: float =Field(gt=0)
    items: list["SaleProducts"]= Relationship(back_populates='sale')
    

class SaleProducts(SQLModel,table=True):
    sale_id: int = Field(primary_key=True,foreign_key='sale.id')
    product_id: int = Field(primary_key=True,foreign_key='product.id')
    unit_price: float = Field(ge=0)
    quantity: int = Field(gt=0)
    sale: "Sale" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates='sale_items')

