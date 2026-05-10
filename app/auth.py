from datetime import datetime, timedelta, timezone
from typing import Annotated
from enum import Enum
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlmodel import Session, select
from .models import User as Userdb, Role, Permission
from .schemas import TokenData
from .database import SessionDep

from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class PermissionsEnum(str, Enum):
    CREATE_USER = "create_user"
    DELETE_USER = "delete_user"
    VIEW_USER = "view_users"
    UPDATE_USER = "update_user"
    CHANGE_PERMISSIONS = "change_permissions"

    # Inventario
    VER_INVENTARIO = "ver_inventario"
    GESTIONAR_INVENTARIO = "gestionar_inventario"

    


class RoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"
    STAFF = "staff"


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(db: SessionDep, email: str):
    user_in_db = db.exec(select(Userdb).where(Userdb.email == email))
    if not user_in_db:
        raise HTTPException(status_code=404, detail="Hero not found")
    return user_in_db.first()


def authenticate_user(db: SessionDep, email: str, password: str):
    user = get_user(db, email)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: SessionDep
) -> Userdb:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[Userdb, Depends(get_current_user)],
) -> Userdb:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_permissions(db: Session):
    permissions = list(PermissionsEnum)

    existing_permissions = db.exec(select(Permission)).all()

    existing_names = {p.name for p in existing_permissions}

    for perm in permissions:
        if perm.value not in existing_names:
            db.add(Permission(name=perm.value))

    db.commit()


def create_role(db: Session, role_name: RoleEnum):
    role = db.exec(select(Role).where(Role.name == role_name.value)).first()
    if not role:
        role = Role(name=role_name.value)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def assign_permissions_to_role(
    db: Session, role: Role, permission_names: list[PermissionsEnum]
):
    permissions_str = [p.value for p in permission_names]
    permissions = db.exec(
        select(Permission).where(Permission.name.in_(permissions_str))
    ).all()

    if len(permissions) != len(permission_names):
        raise ValueError("Some permissions not found in DB")

    existing = {p.name for p in role.permissions}

    update = False

    for perm in permissions:
        if perm.name not in existing:
            role.permissions.append(perm)
            update = True

    if update:
        db.commit()
        db.refresh(role)
    return role


def require_permission(permission_name: PermissionsEnum):
    def checker(user: Annotated[Userdb, Depends(get_current_active_user)]):

        if not user.role:
            raise HTTPException(403, "User has no role assigned")

        user_permissions = {p.name for p in user.role.permissions}

        if permission_name.value not in user_permissions:
            raise HTTPException(403, "Not enough permissions")

        return user

    return checker


def require_role(role_name: RoleEnum):
    def checker(user: Annotated[Userdb, Depends(get_current_active_user)]):
        if user.role.name != role_name.value:
            raise HTTPException(status_code=403, detail="required role not found")
        return user

    return checker


def assign_role_to_user(user: Userdb, role_name: RoleEnum, db: Session):

    role_db = db.exec(select(Role).where(Role.name == role_name.value)).first()

    if not role_db:
        raise HTTPException(status_code=404, detail="role not found")

    if user.role_id == role_db.id:
        return user

    user.role = role_db

    db.commit()
    db.refresh(user)
    return user
