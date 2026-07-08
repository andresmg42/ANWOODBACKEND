from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from ..auth import (
    PermissionsEnum,
    RoleEnum,
    assign_role_to_user,
    get_password_hash,
    require_permission,
    require_role,
)
from ..database import SessionDep
from ..models import User as Userdb
from ..schemas import ChangeRole, MessageResponse, UserIn, UserPublic, UserUpdate

router = APIRouter(tags=["users"])


@router.post(
    "/users",
    response_model=UserPublic,
    summary="Registrar usuario",
)
async def create_user(user: UserIn, db: SessionDep):
    existing_user = db.exec(
        select(Userdb).where(Userdb.username == user.username)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exisits")
    hashed_password = get_password_hash(user.password)
    db_user = Userdb(
        **user.model_dump(exclude={"password"}),
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get(
    "/users",
    response_model=list[UserPublic],
    summary="Listar usuarios",
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def get_users(db: SessionDep):
    return db.exec(select(Userdb)).all()


@router.get(
    "/users/{user_id}",
    response_model=UserPublic,
    summary="Obtener usuario por ID",
    dependencies=[Depends(require_permission(PermissionsEnum.VIEW_USER))],
)
async def get_user(db: SessionDep, user_id: int):
    user = db.get(Userdb, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return user


@router.patch(
    "/users/{user_id}/delete",
    response_model=MessageResponse,
    summary="Desactivar usuario (soft delete)",
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
    "/users/{user_id}",
    response_model=UserPublic,
    summary="Actualizar usuario",
    dependencies=[Depends(require_permission(PermissionsEnum.UPDATE_USER))],
)
async def update_user(user_id: int, payload: UserUpdate, db: SessionDep):
    user = db.get(Userdb, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    user_data = payload.model_dump(exclude_unset=True)
    if not user_data:
        raise HTTPException(status_code=400, detail="No data provided for update")
    if "password" in user_data:
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
    user.sqlmodel_update(user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/role",
    response_model=UserPublic,
    summary="Cambiar rol de usuario",
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
