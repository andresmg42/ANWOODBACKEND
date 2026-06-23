from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Header, HTTPException
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, Field

from sqlmodel import select

from ..auth import ALGORITHM, SECRET_KEY
from ..database import SessionDep
from ..models import User
from ..services.assistant_executor import AssistantExecutor
from ..services.gemini_service import GEMINI_API_KEY, get_gemini_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    capability: str | None = None


def _get_user_from_token(authorization: str | None, db: SessionDep) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token or not SECRET_KEY or not ALGORITHM:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return db.exec(select(User).where(User.username == username)).first()
    except InvalidTokenError:
        return None


def _session_context(user: User | None) -> str:
    if user:
        return (
            f"[Sesión activa: usuario '{user.username}' autenticado (id={user.id}). "
            "Puedes usar consultar_cotizaciones, generar_cotizacion y herramientas de carrito.]"
        )
    return (
        "[Sesión: usuario NO autenticado. "
        "Solo están disponibles consultas públicas de catálogo, inventario e información.]"
    )


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    body: AssistantChatRequest,
    db: SessionDep,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="El asistente no está configurado. Falta GEMINI_API_KEY",
        )

    try:
        service = get_gemini_service()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    user = _get_user_from_token(authorization, db)
    executor = AssistantExecutor(db, user_id=user.id if user else None)
    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        result = service.chat(
            body.message,
            history,
            executor,
            session_context=_session_context(user),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error al comunicarse con Gemini: {exc}",
        ) from exc

    return AssistantChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        capability=result.get("capability"),
    )
