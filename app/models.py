from sqlmodel import Field, SQLModel, Relationship


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
    roles: list[Role] = Relationship(
        back_populates="permissions", link_model=RolePermissions
    )


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    email: str | None = Field(default=None)
    full_name: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    disabled: bool | None = Field(default=False)
    role_id: int | None = Field(foreign_key="role.id", default=None)
    role: Role | None = Relationship(back_populates="users")
    hashed_password: str
