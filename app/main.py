from fastapi import FastAPI
from .database import create_db_and_tables, SessionDep
from contextlib import asynccontextmanager
from .routers import auth, users, Inventory, cart


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(cart.router) 
app.include_router(Inventory.router)

# Health check
@app.get("/health")
def health_check(session: SessionDep):
    return {"ok": True}