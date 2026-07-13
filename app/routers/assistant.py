from typing import Annotated, Literal, Optional
import uuid
from pydantic import ValidationError
import jwt
from fastapi import APIRouter, Header, HTTPException,UploadFile,File, Form
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, Field

from sqlmodel import select

from ..auth import ALGORITHM, SECRET_KEY
from ..database import SessionDep
from ..models import User
from ..services.assistant_executor import AssistantExecutor
from ..services.gemini_service import GEMINI_API_KEY, get_gemini_service
import json
router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


# class AssistantChatRequest(BaseModel):
#     message: str = Field(..., min_length=1, max_length=2000)
#     image: UploadFile | None =None
#     history: list[ChatMessage] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    capability: str | None = None
    session_id: str


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
    db: SessionDep,
    message: str = Form(..., min_length=1, max_length=2000),
    history: str = Form(default="[]"),
    session_id: str | None = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    try:

        raw_history=json.loads(history)
        validated_history=[ChatMessage(**m) for m in raw_history]

    except (json.JSONDecodeError,ValidationError,TypeError) as exc:
        raise HTTPException(status_code=422, detail=f'Invalid History: {exc}')
    


    
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
    chat_history = [{"role": m.role, "content": m.content} for m in validated_history]
    active_session_id = session_id or str(uuid.uuid4())

    try:
        result = await  service.chat(
            message,
            chat_history,
            executor,
            image,
            session_context=_session_context(user),
            session_id=active_session_id,
            
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
        session_id=result["session_id"],
    )


@router.delete("/session/{session_id}")
async def delete_assistant_session(session_id: str):
    service = get_gemini_service()
    service.clear_session(session_id)
    return {"message": f"Assistant session {session_id} cleared", "session_id": session_id}
