from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from ..schemas import ProductCreate,ProductPublic,UserPublic,ProductUpdate,CreateSale,SalePublic
from ..database import SessionDep 
from ..models import Sale,User,SaleProducts
from ..auth import get_current_active_user,require_permission,PermissionsEnum,require_role,RoleEnum

router=APIRouter()

@router.post("/sales/{user_id}",response_model=SalePublic,dependencies=[Depends(require_permission(PermissionsEnum.CREATE_SALE))])
async def create_sale(user_id:int,sale_in:CreateSale,db:SessionDep):

    user_db=db.get(User,user_id)

    if not user_db:
        raise HTTPException(404, 'user not found')
    
    total_price=sum(item.unit_price * item.quantity for item in sale_in.items)
    
    new_sale=Sale(user=user_db,total_price=total_price)

    
    for item in sale_in.items:

        sale_item=SaleProducts(
            **item.model_dump(),
            sale=new_sale
        )

        db.add(sale_item)
    
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)

    return new_sale


    