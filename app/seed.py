from sqlmodel import Session
from .auth import create_permissions, create_role, assign_permissions_to_role
from .auth import RoleEnum, PermissionsEnum


def seed_data(db: Session):
    create_permissions(db)
    admin = create_role(db, RoleEnum.ADMIN)
    user = create_role(db, RoleEnum.USER)
    assign_permissions_to_role(db, admin, list(PermissionsEnum))
    assign_permissions_to_role(
        db,
        user,
        [
            PermissionsEnum.CREATE_USER,
            PermissionsEnum.VIEW_USER,
        ],
    )
