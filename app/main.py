from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_db_and_tables, SessionDep
from contextlib import asynccontextmanager
from .openapi import API_DESCRIPTION, API_TITLE, API_VERSION, OPENAPI_TAGS
from .routers import (
    auth,
    quotation_detail,
    users,
    lote_inventory,
    cart,
    pieza_madera,
    tipos_madera,
    medidas,
    categorias,
    configuration,
    quotation,
    metricas,
    proveedores,
)
from .schemas import HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://anwoodfrontend.vercel.app",
        "https://angwood.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(lote_inventory.router)
app.include_router(proveedores.router)
app.include_router(pieza_madera.router)
app.include_router(tipos_madera.router)
app.include_router(medidas.router)
app.include_router(categorias.router)
app.include_router(configuration.router)
app.include_router(quotation.router)
app.include_router(quotation_detail.router)
app.include_router(metricas.router)


@app.get(
    "/health",
    tags=["health"],
    summary="Comprobar estado del servicio",
    response_model=HealthResponse,
)
def health_check(_session: SessionDep):
    return {"ok": True}
