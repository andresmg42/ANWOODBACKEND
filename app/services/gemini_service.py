from typing import Any
import uuid
from fastapi import UploadFile
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import asyncio
from .assistant_executor import AssistantExecutor
from .assistant_tools import (
    FUNCTION_DECLARATIONS,
    FUNCTION_TO_CAPABILITY,
    SYSTEM_PROMPT,
)
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

MAX_FUNCTION_TURNS = 5


_session_histories: dict[str, list[dict[str, str]]] = {}


class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY no está configurada en el entorno"
            )
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.tools = types.Tool(function_declarations=FUNCTION_DECLARATIONS)
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.tools],
        )

    async def _build_contents(
        self,
        message: str,
        history: list[dict[str, str]],
        image: UploadFile | None = None,
        session_context: str | None = None,
    ) -> list[types.Content]:
        contents: list[types.Content] = []

        for entry in history:
            role = "user" if entry["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=entry["content"])])
            )

        user_message = message
        if session_context:
            user_message = f"{session_context}\n\n{message}"

        image_part:types.Part | None = None
        if image is not None:
            image_bytes= await image.read()

            if len(image_bytes)>0:
                mime_type= image.content_type or "image/jpeg"
                image_part= types.Part.from_bytes(data=image_bytes,mime_type=mime_type)

                

        parts: list[types.Part] = [types.Part(text=user_message)]
        if image_part is not None:
            parts.append(image_part)

        contents.append(types.Content(role="user", parts=parts))
        return contents

    def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        return list(_session_histories.get(session_id, []))

    def save_session_history(
        self,
        session_id: str,
        history: list[dict[str, str]],
        assistant_reply: str,
        user_message: str,
    ) -> None:
        _session_histories[session_id] = [
            *history,
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_reply},
        ]

    def clear_session(self, session_id: str) -> None:
        _session_histories.pop(session_id, None)

    def _extract_function_call(self, candidate) -> types.FunctionCall | None:
        if not candidate or not candidate.content or not candidate.content.parts:
            return None
        for part in candidate.content.parts:
            if part.function_call:
                return part.function_call
        return None

    def _build_function_response_part(
        self,
        name: str,
        result: dict[str, Any],
        call_id: str | None = None,
    ) -> types.Part:
        fn_kwargs: dict[str, Any] = {"name": name, "response": result}
        if call_id:
            fn_kwargs["id"] = call_id
        return types.Part(function_response=types.FunctionResponse(**fn_kwargs))

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]],
        executor: AssistantExecutor,
        image: UploadFile | None = None,
        session_context: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        active_session_id = session_id or str(uuid.uuid4())
        session_history = self.get_session_history(active_session_id)
        effective_history = history if history else session_history
        contents = await self._build_contents(
            
            message,
            effective_history,
            image,
            session_context,
        )

        intent: str | None = None
        capability: str | None = None
        last_response = None

        for _ in range(MAX_FUNCTION_TURNS):
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=GEMINI_MODEL,
                contents=contents,
                config=self.config,
            )
            last_response = response
            candidate = response.candidates[0] if response.candidates else None
            fc = self._extract_function_call(candidate)

            if not fc:
                break

            intent = fc.name
            capability = FUNCTION_TO_CAPABILITY.get(fc.name)
            args = dict(fc.args) if fc.args else {}
            result = executor.execute(fc.name, args)

            contents.append(candidate.content)
            fn_response = self._build_function_response_part(
                name=fc.name,
                result=result,
                call_id=getattr(fc, "id", None),
            )
            contents.append(types.Content(role="user", parts=[fn_response]))

        reply = (
            (last_response.text if last_response else None)
            or "Lo siento, no pude procesar tu consulta."
        )
        self.save_session_history(
            active_session_id,
            effective_history,
            reply.strip(),
            message,
        )
        return {
            "reply": reply.strip(),
            "intent": intent,
            "capability": capability,
            "session_id": active_session_id,
        }


_gemini_service: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
