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


def _ensure_woodpiece_dimension_columns():
    inspector = inspect(engine)

    if "woodpiece" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("woodpiece")}
    statements = []

    if "ancho_in" not in columns:
        statements.append("ALTER TABLE woodpiece ADD COLUMN ancho_in NUMERIC")
    if "alto_in" not in columns:
        statements.append("ALTER TABLE woodpiece ADD COLUMN alto_in NUMERIC")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_woodpiece_calidad_column():
    inspector = inspect(engine)

    if "woodpiece" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("woodpiece")}
    if "calidad" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE woodpiece ADD COLUMN calidad VARCHAR"))


def _drop_woodpiece_fecha_ingreso_column():
    inspector = inspect(engine)

    if "woodpiece" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("woodpiece")}
    if "fecha_ingreso" not in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE woodpiece DROP COLUMN fecha_ingreso")
        )


def _migrate_cubicacion_fields():
    inspector = inspect(engine)

    if "categoria" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("categoria")}
        if "permite_cubicacion" in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE categoria DROP COLUMN permite_cubicacion")
                )

    if "tipo_madera" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("tipo_madera")}
        if "permite_cubicacion" in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE tipo_madera DROP COLUMN permite_cubicacion")
                )

    if "medida" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("medida")}
    if "permite_cubicacion" in columns and "cubica" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE medida RENAME COLUMN permite_cubicacion TO cubica")
            )
    elif "cubica" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE medida ADD COLUMN cubica BOOLEAN NOT NULL DEFAULT TRUE")
            )


def _drop_cotizacion_tipo_compra_column():
    inspector = inspect(engine)

    if "cotizacion" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("cotizacion")}
    if "tipo_compra" not in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE cotizacion DROP COLUMN tipo_compra")
        )


def _drop_loteinventory_proveedor_column():
    inspector = inspect(engine)

    if "loteinventory" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("loteinventory")}
    if "proveedor" not in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE loteinventory DROP COLUMN proveedor")
        )


def _ensure_cotizacion_via_transporte_column():
    inspector = inspect(engine)

    if "cotizacion" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("cotizacion")}
    if "via_transporte" in columns:
        return

    dialect_name = engine.dialect.name
    if dialect_name == "postgresql":
        statement = (
            "ALTER TABLE cotizacion "
            "ADD COLUMN via_transporte VARCHAR NOT NULL DEFAULT 'tierra'"
        )
    else:
        statement = (
            "ALTER TABLE cotizacion "
            "ADD COLUMN via_transporte VARCHAR NOT NULL DEFAULT 'tierra'"
        )

    with engine.begin() as connection:
        connection.execute(text(statement))


def _ensure_via_transporte_configurations():
    inspector = inspect(engine)

    if "configuracion" not in inspector.get_table_names():
        return

    config_specs = [
        (
            "costo_transporte_tierra_defecto",
            "costo_transporte_defecto",
            "500000",
            "Costo de transporte por defecto vía terrestre",
        ),
        (
            "costo_transporte_mar_defecto",
            "costo_transporte_defecto",
            "500000",
            "Costo de transporte por defecto vía marítima",
        ),
        (
            "costo_cargue_tierra_defecto",
            "costo_cargue_defecto",
            "200000",
            "Costo de cargue por defecto vía terrestre",
        ),
        (
            "costo_cargue_mar_defecto",
            "costo_cargue_defecto",
            "200000",
            "Costo de cargue por defecto vía marítima",
        ),
        (
            "costo_descargue_tierra_defecto",
            "costo_descargue_defecto",
            "200000",
            "Costo de descargue por defecto vía terrestre",
        ),
        (
            "costo_descargue_mar_defecto",
            "costo_descargue_defecto",
            "200000",
            "Costo de descargue por defecto vía marítima",
        ),
        (
            "tasa_salvoconducto_tierra_por_m3",
            "tasa_salvoconducto_por_m3",
            "10",
            "Tasa EPA/salvoconducto por m³ vía terrestre",
        ),
        (
            "tasa_salvoconducto_mar_por_m3",
            "tasa_salvoconducto_por_m3",
            "10",
            "Tasa EPA/salvoconducto por m³ vía marítima",
        ),
    ]

    with engine.begin() as connection:
        for new_key, legacy_key, default_val, descripcion in config_specs:
            exists = connection.execute(
                text("SELECT 1 FROM configuracion WHERE clave = :clave"),
                {"clave": new_key},
            ).first()
            if exists:
                continue

            legacy = connection.execute(
                text("SELECT valor FROM configuracion WHERE clave = :clave"),
                {"clave": legacy_key},
            ).first()
            valor = legacy[0] if legacy else default_val

            connection.execute(
                text(
                    "INSERT INTO configuracion (clave, valor, descripcion) "
                    "VALUES (:clave, :valor, :descripcion)"
                ),
                {"clave": new_key, "valor": str(valor), "descripcion": descripcion},
            )


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _ensure_tipo_madera_imagenes_column()
    _drop_tipo_madera_densidad_column()
    _ensure_woodpiece_dimension_columns()
    _ensure_woodpiece_calidad_column()
    _drop_woodpiece_fecha_ingreso_column()
    _migrate_cubicacion_fields()
    _drop_cotizacion_tipo_compra_column()
    _drop_loteinventory_proveedor_column()
    _ensure_cotizacion_via_transporte_column()
    _ensure_via_transporte_configurations()


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
