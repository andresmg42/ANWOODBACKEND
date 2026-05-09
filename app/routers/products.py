from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from ..schemas import ProductCreate,ProductPublic,UserPublic,ProductUpdate
from ..database import SessionDep 
from ..models import Product
from ..auth import get_current_active_user,require_permission,PermissionsEnum


router=APIRouter()

@router.post("/products",response_model=ProductPublic,dependencies=[
    Depends(require_permission(PermissionsEnum.CREATE_PRODUCTS))
    ])
async def create_products(product:ProductCreate,db:SessionDep):
    existing_product=db.exec(select(Product).where(Product.code==product.code)).first()
    if existing_product:
        raise HTTPException(status=400,detail="Product alreaduy exists")
    valid_db_product=Product.model_validate(product)
    db.add(valid_db_product)
    db.commit()
    db.refresh(valid_db_product)
    return valid_db_product

@router.get("/products",response_model=list[ProductPublic])
async def get_products(
    db:SessionDep,
    offset:int=0,
    limit:Annotated[int,Query(le=100)]=100
    ):
    products=db.exec(select(Product).offset(offset).limit(limit)).all()
    return products

@router.get("/products/{product_id}",response_model=ProductPublic)
async def get_products_by_id(product_id:int,db:SessionDep):
    product=db.get(Product,product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{product_id}",response_model=ProductPublic,dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_PRODUCTS))])
def update_product(product_id:int,product:ProductUpdate,db:SessionDep):
    product_db=db.get(Product,product_id)
    if not product_db:
        raise HTTPException(status_code=404,detail="Product not found")
    product_data=product.model_dump(exclude_unset=True)
    if not product_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
    product_db.sqlmodel_update(product_data)
    db.add(product_db)
    db.commit()
    db.refresh(product_db)
    return product_db

@router.patch("/products/{product_id}/delete",dependencies=[Depends(require_permission(PermissionsEnum.DELETE_PRODUCTS))])
def inactivate_product(product_id:int,db:SessionDep):
    product_db=db.get(Product,product_id)
    if not product_db:
        raise HTTPException(status_code=404,detail="Product not found")
    if not product_db.is_active:
        return {'detail':'the product already was deleted'}
    product_db.is_active=False
    db.add(product_db)
    db.commit()
    db.refresh(product_db)
    return {'detail':"Product deleted successfully"}





