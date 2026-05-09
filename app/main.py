from typing import Annotated
from .auth import create_permissions, create_role, assign_permissions_to_role
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel
from .database import get_session,create_db_and_tables,SessionDep,engine
from contextlib import asynccontextmanager
from .routers import auth, users, products, sales
from .seed import seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
   create_db_and_tables()
   yield

app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(sales.router)


@app.get("/health")
def health_check(session:SessionDep):
    return {"ok": True}


