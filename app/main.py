from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_db_and_tables, SessionDep
from .create_admin_user import init_db_and_admin 
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
    metricas,
    chatbot,
    assistant,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("Ejecutando script de creación de administrador y migraciones...")
    try:
        init_db_and_admin()  
        print("Script ejecutado con éxito.")
    except Exception as e:
        print(f"Error al crear el admin: {e}")

    yield
    


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://anwoodfrontend.vercel.app",
        "https://angwood.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(metricas.router)
app.include_router(chatbot.router)
app.include_router(assistant.router)


# Health check
@app.get("/health")
def health_check(_session: SessionDep):
    return {"ok": True}
