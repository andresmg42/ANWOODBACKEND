from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_db_and_tables, SessionDep
from contextlib import asynccontextmanager
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
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(lote_inventory.router)
app.include_router(pieza_madera.router)
app.include_router(tipos_madera.router)
app.include_router(medidas.router)
app.include_router(categorias.router)
app.include_router(configuration.router)
app.include_router(quotation.router)
app.include_router(quotation_detail.router)


# Health check
@app.get("/health")
def health_check(_session: SessionDep):
    return {"ok": True}
