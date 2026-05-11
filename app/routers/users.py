from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi import APIRouter
from ..schemas import UserPublic, UserInDB, UserIn, UserPublic, ChangeRole
from ..auth import (
    get_current_active_user,
    get_password_hash,
    assign_role_to_user,
    require_permission,
    RoleEnum,
    PermissionsEnum,
    require_role,
)
from ..database import SessionDep
from ..models import User as Userdb, Role
from sqlmodel import select

router = APIRouter()


@router.post("/users", response_model=UserPublic)
async def create_user(user: UserIn, db: SessionDep):
    existing_user = db.exec(
        select(Userdb).where(Userdb.username == user.username)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exisits")
    hashed_password = get_password_hash(user.password)
    db_user = UserInDB(**user.model_dump(), hashed_password=hashed_password)
    valid_db_user = Userdb.model_validate(db_user)
    db.add(valid_db_user)
    db.commit()
    db.refresh(valid_db_user)
    assign_role_to_user(valid_db_user, RoleEnum.USER, db)
    return valid_db_user


@router.get(
    "/users",
    response_model=list[Userdb],
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def get_users(db: SessionDep):

    users = db.exec(select(Userdb)).all()

    return users


@router.get(
    "/users/{user_id}",
    response_model=UserPublic,
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def get_user(db: SessionDep, user_id: int):

    user = db.get(Userdb, user_id)

    if not user:
        raise HTTPException(404, "user not found")

    return user


@router.patch(
    "/users/{user_id}/delete",
    dependencies=[Depends(require_permission(PermissionsEnum.DELETE_USER))],
)
async def delete_user(user_id: int, db: SessionDep):

    user = db.get(Userdb, user_id)

    if not user:
        raise HTTPException(404, "user not found")

    if user.disabled:
        return {"message": f"user whit id {user_id} already deleted"}

    user.disabled = True

    db.commit()
    db.refresh(user)
    return {"message": f"user with id {user_id} deleted successfully"}


@router.patch(
    "/users/{user_id}/role",
    response_model=UserPublic,
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)
def change_user_role(
    user_id: int,
    new_role: ChangeRole,
    session: SessionDep,
):
    user = session.get(Userdb, user_id)

    if not user:
        raise HTTPException(404, "User not found")

    if not new_role.name:
        raise HTTPException(400, "role name is required")

    try:
        role_enum = RoleEnum(new_role.name)

    except ValueError:
        raise HTTPException(400, "invalid role")

    return assign_role_to_user(user, role_enum, session)
