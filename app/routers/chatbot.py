import asyncio
from fastapi import APIRouter
from dotenv import load_dotenv
import uuid
from ..schemas import PostHumanQueryPayload
from ..services.chatbot_service import _run_query,clear_session,get_schema
import logging

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/human_query", name="Human Query", operation_id="post_human_query")
async def human_query(payload: PostHumanQueryPayload):

    session_id = payload.session_id or str(uuid.uuid4())

    try:
        result = await asyncio.wait_for(
            _run_query(payload.human_query, session_id), timeout=120.0
        )

        return {"session_id": session_id, **result}
    except asyncio.TimeoutError:
        return {"error": "La consulta tardó demasiado, intenta de nuevo"}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    clear_session(session_id)
    return {"message": f"Session {session_id} cleared"}
