from sqlmodel import Session, select
from .database import engine, create_db_and_tables
import os
from dotenv import load_dotenv
from .auth import get_password_hash, assign_role_to_user, RoleEnum
from .models import User
from .seed import seed_data

load_dotenv()


PASSWORD = os.getenv("PASSWORD")
USERNAME = os.getenv("SUPERUSER_USERNAME")
EMAIL = os.getenv("EMAIL")


def create_super_user(db: Session):

    if not PASSWORD or not USERNAME:
        print("USER DATA IS WRONG")
        return

    existing = db.exec(select(User).where(User.username == USERNAME)).first()

    if existing:
        print("user already exists")
        return
    hashed_password = get_password_hash(PASSWORD)

    user = User(
        username=USERNAME,
        email=EMAIL,
        hashed_password=hashed_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    assign_role_to_user(user, RoleEnum.ADMIN, db)


# 👇 NUEVA FUNCIÓN CONTENEDORA
def init_db_and_admin():
    with Session(engine) as db:
        create_db_and_tables()  # Crea tablas si no existen
        seed_data(db)  # Agrega datos semilla
        create_super_user(db)  # Crea al admin
        print("Database initialized and super user verified/created successfully.")


if __name__ == "__main__":
    init_db_and_admin()
