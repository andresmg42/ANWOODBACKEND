from decimal import Decimal

from sqlmodel import Session, select

from .auth import PermissionsEnum, RoleEnum
from .auth import assign_permissions_to_role, create_permissions, create_role
from .models import Categoria, Configuration, LoteInventory, Medida, TipoMadera, WoodPiece


def _upsert_configuration(db: Session, clave: str, valor: str, descripcion: str):
    config = db.exec(select(Configuration).where(Configuration.clave == clave)).first()
    if config:
        config.valor = valor
        config.descripcion = descripcion
        db.add(config)
        return

    db.add(Configuration(clave=clave, valor=valor, descripcion=descripcion))


def seed_data(db: Session):
    create_permissions(db)
    admin = create_role(db, RoleEnum.ADMIN)
    staff = create_role(db, RoleEnum.STAFF)
    user = create_role(db, RoleEnum.USER)

    assign_permissions_to_role(db, admin, list(PermissionsEnum))
    assign_permissions_to_role(
        db,
        staff,
        [
            PermissionsEnum.CREATE_USER,
            PermissionsEnum.VIEW_USER,
            PermissionsEnum.UPDATE_USER,
            PermissionsEnum.VER_INVENTARIO,
            PermissionsEnum.GESTIONAR_INVENTARIO,
            PermissionsEnum.CREATE_COTIZACION,
            PermissionsEnum.VIEW_COTIZACION,
            PermissionsEnum.UPDATE_COTIZACION,
        ],
    )
    assign_permissions_to_role(
        db,
        user,
        [
            PermissionsEnum.CREATE_USER,
            PermissionsEnum.VIEW_USER,
            PermissionsEnum.VIEW_COTIZACION,
        ],
    )

    _upsert_configuration(
        db,
        "precio_epa_por_metro",
        "1500",
        "Costo del salvoconducto EPA por metro transportado",
    )
    _upsert_configuration(
        db,
        "precio_cargue_terrestre_por_metro",
        "0",
        "Costo de cargue terrestre por metro",
    )
    _upsert_configuration(
        db,
        "precio_descargue_terrestre_por_metro",
        "0",
        "Costo de descargue terrestre por metro",
    )
    _upsert_configuration(
        db,
        "precio_cargue_maritimo_por_metro",
        "0",
        "Costo de cargue marítimo por metro",
    )
    _upsert_configuration(
        db,
        "precio_descargue_maritimo_por_metro",
        "0",
        "Costo de descargue marítimo por metro",
    )
    db.commit()

    categoria = db.exec(select(Categoria).where(Categoria.nombre == "Madera Corta")).first()
    if categoria:
        return

    madera_corta = Categoria(
        nombre="Madera Corta",
        estrategia_precio="por_volumen",
        permite_cubicacion=True,
        formula_cubicacion="largo_x_alto_x_ancho_div_10",
    )
    madera_larga = Categoria(
        nombre="Madera Larga",
        estrategia_precio="por_volumen",
        permite_cubicacion=True,
        formula_cubicacion="largo_x_alto_x_ancho_div_10",
    )
    db.add_all([madera_corta, madera_larga])
    db.commit()
    db.refresh(madera_corta)
    db.refresh(madera_larga)

    tipos_madera = [
        TipoMadera(
            categoria_id=madera_corta.id,
            nombre="Chaquiro",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("8000"),
        ),
        TipoMadera(
            categoria_id=madera_corta.id,
            nombre="Chanúl",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("8000"),
        ),
        TipoMadera(
            categoria_id=madera_corta.id,
            nombre="Carbonero",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("8000"),
        ),
        TipoMadera(
            categoria_id=madera_corta.id,
            nombre="Caimito",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("8000"),
        ),
        TipoMadera(
            categoria_id=madera_corta.id,
            nombre="Revoltura",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("8000"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Flor morado",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("3500"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Popa",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("2000"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Tangare",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("1600"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Algarrobo",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("3000"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Roble",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("3000"),
        ),
        TipoMadera(
            categoria_id=madera_larga.id,
            nombre="Cedro",
            densidad_kg_m3=Decimal("0"),
            precio_por_metro=Decimal("3000"),
        ),
    ]
    db.add_all(tipos_madera)
    db.commit()

    medidas = [
        Medida(
            ancho_in=Decimal("2"),
            alto_in=Decimal("5"),
            etiqueta="2x5",
            es_estandar=True,
            permite_cubicacion=False,
        ),
        Medida(
            ancho_in=Decimal("3"),
            alto_in=Decimal("6"),
            etiqueta="3x6",
            es_estandar=True,
            permite_cubicacion=True,
        ),
        Medida(
            ancho_in=Decimal("2"),
            alto_in=Decimal("8"),
            etiqueta="2x8",
            es_estandar=True,
            permite_cubicacion=True,
        ),
    ]
    db.add_all(medidas)
    db.commit()
    for medida in medidas:
        db.refresh(medida)

    lote = LoteInventory(
        codigo_lote="LOTE-001",
        proveedor="Proveedor Semilla",
        costo_total=Decimal("100000"),
        estado="activo",
    )
    db.add(lote)
    db.commit()
    db.refresh(lote)

    chaquiro = db.exec(select(TipoMadera).where(TipoMadera.nombre == "Chaquiro")).first()
    popa = db.exec(select(TipoMadera).where(TipoMadera.nombre == "Popa")).first()
    medida_3x6 = db.exec(select(Medida).where(Medida.etiqueta == "3x6")).first()
    medida_2x5 = db.exec(select(Medida).where(Medida.etiqueta == "2x5")).first()

    if chaquiro and popa and medida_3x6 and medida_2x5:
        pieza1 = WoodPiece(
            tipo_madera_id=chaquiro.id,
            medida_id=medida_3x6.id,
            lote_id=lote.id,
            largo_m=Decimal("4"),
            volumen_m3=Decimal("7.2"),
            cantidad=20,
            cantidad_reservada=0,
            estado="disponible",
            costo_unitario=Decimal("40000"),
            precio_unitario=Decimal("57600"),
        )
        pieza2 = WoodPiece(
            tipo_madera_id=popa.id,
            medida_id=medida_2x5.id,
            lote_id=lote.id,
            largo_m=Decimal("5"),
            volumen_m3=Decimal("0"),
            cantidad=10,
            cantidad_reservada=0,
            estado="disponible",
            costo_unitario=Decimal("7000"),
            precio_unitario=Decimal("10000"),
        )
        db.add_all([pieza1, pieza2])
        db.commit()

