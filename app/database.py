from typing import Annotated

from fastapi import Depends
from sqlalchemy import inspect, text, event
from sqlmodel import Session, SQLModel, create_engine
from dotenv import load_dotenv
import os

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(database_url, connect_args=connect_args)


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if database_url and database_url.startswith("sqlite"):
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)


def _ensure_tipo_madera_imagenes_column():
    inspector = inspect(engine)

    if "tipo_madera" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("tipo_madera")}
    if "imagenes" in columns:
        return

    dialect_name = engine.dialect.name
    if dialect_name == "postgresql":
        statement = (
            "ALTER TABLE tipo_madera "
            "ADD COLUMN imagenes JSON NOT NULL DEFAULT '[]'::json"
        )
    else:
        statement = (
            "ALTER TABLE tipo_madera "
            "ADD COLUMN imagenes JSON NOT NULL DEFAULT '[]'"
        )

    with engine.begin() as connection:
        connection.execute(text(statement))


def _drop_tipo_madera_densidad_column():
    inspector = inspect(engine)

    if "tipo_madera" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("tipo_madera")}
    if "densidad_kg_m3" not in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE tipo_madera DROP COLUMN densidad_kg_m3")
        )


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_tipo_madera_imagenes_column()
    _drop_tipo_madera_densidad_column()


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
