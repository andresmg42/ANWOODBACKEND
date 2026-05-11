from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_db_and_tables, SessionDep
from contextlib import asynccontextmanager
from .routers import auth, users, lote_inventory, cart, pieza_madera, client


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(lote_inventory.router)
app.include_router(pieza_madera.router)
app.include_router(client.router)


# Health check
@app.get("/health")
def health_check(session: SessionDep):
    return {"ok": True}
