from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_db_and_tables, SessionDep
from contextlib import asynccontextmanager
from .routers import auth, users, Inventory, cart


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router) 
#app.include_router(Inventory.router)
app.include_router(
    Inventory.router, 
    prefix="/api/v1/inventory" #/api/v1/inventory/piezas
)

# Health check
@app.get("/health")
def health_check(session: SessionDep):
    return {"ok": True}