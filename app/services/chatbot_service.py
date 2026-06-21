import os
import asyncio
from typing import Any
from google import genai
from sqlalchemy import text, inspect
from google.genai.types import GenerateContentConfig
import time
from ..schemas import ResponseLLM
from ..database import engine


SQL_MODEL = "gemini-3.1-flash-lite"
ANSWER_MODEL = "gemini-3.1-flash-lite"
SESSION_TTL_SECONDS = 60 * 30
EXAMPLE = ResponseLLM(
    sql_query="SELECT * FROM zone_zone WHERE campus='Melendez'"
)
INTERNAL_TABLES = {
    "user",
    "rolepermissions",
    "permission",
    "role",
    "itemcart",
    "configuracion",
    "cart",
}

session_store: dict[str, dict] = {}

BUSINESS_POLICIES_PATH=os.path.join(os.path.dirname(__file__),"..","..","policies.txt")

CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
INSPECTOR = inspect(engine)


def load_policies()->str:
    with open(BUSINESS_POLICIES_PATH,"r", encoding="utf-8") as f:
        return f.read()

BUSINESS_POLICIES= load_policies()

def get_schema() -> str:
    lines = []

    inspector=INSPECTOR

    for table in inspector.get_table_names():
        if table in INTERNAL_TABLES:
            continue

        pk_columns = set(
            inspector.get_pk_constraint(table).get("constrained_columns", [])
        )

        fk_map = {}
        for fk in inspector.get_foreign_keys(table):
            for col in fk["constrained_columns"]:
                ref_table = fk["referred_table"]
                ref_cols = ", ".join(fk["referred_columns"])
                fk_map[col] = f"{ref_table}({ref_cols})"

        unique_constraints = []
        for idx in inspector.get_indexes(table):
            if idx["unique"]:
                unique_constraints.append(idx["column_names"])

        lines.append(f"TABLE {table}")

        for column in inspector.get_columns(table):
            name = column["name"]
            col_type = str(column["type"])
            nullability = "NULL" if column["nullable"] else "NOT NULL"

            annotations = []
            if name in pk_columns:
                annotations.append("PK")
            if name in fk_map:
                annotations.append(f"FK → {fk_map[name]}")

            suffix = ("  " + "  ".join(annotations)) if annotations else ""
            lines.append(f"  {name:<20} {col_type:<15} {nullability}{suffix}")

        for unique_cols in unique_constraints:
            lines.append(f"  UNIQUE({', '.join(unique_cols)})")

        lines.append("")

    return "\n".join(lines)

SCHEMA = get_schema()


async def get_or_create_session(
    session_id: str
) -> dict:

    now = time.time()

    expired = [
        sid
        for sid, data in session_store.items()
        if now - data["last_activity"] > SESSION_TTL_SECONDS
    ]

    for sid in expired:
        del session_store[sid]
        print(f"Session {sid} expired and removed")

    if session_id not in session_store:
        sql_chat = CLIENT.chats.create(model=SQL_MODEL)
        answer_chat = CLIENT.chats.create(model=ANSWER_MODEL)
        # Inject schema once on session creation
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: sql_chat.send_message(
                f"""You are a SQL expert assistant. This is the database schema, response format, and constraints 
                    you must follow during the entire session.

                    <database_schema>
                    {SCHEMA}
                    </database_schema>

                    <response_format>
                    You must ALWAYS respond with ONLY a valid JSON object, no markdown, no explanation, no backticks.
                    Exactly this format:
                    {EXAMPLE.model_dump_json()}
                    </response_format>

                    <constraints>
                    <rule>Never include raw numeric IDs or primary keys (e.g., id, pk, *_id) as columns in the response.</rule>
                    <rule>Always replace IDs with their human-readable label by using JOINs when necessary.</rule>
                    <rule>Only generate SELECT statements. Never use INSERT, UPDATE, DELETE or DROP.</rule>
                    <rule>If the question cannot be answered with the available schema, return an empty sql_query field.</rule>
                    </constraints>
                """
            ),
        )
        # Answer agent gets business policies
        await loop.run_in_executor(
            None,
            lambda: answer_chat.send_message(
                f"""You are a business assistant for a wood products company. 
                    You have two sources of knowledge to answer user questions:
                    1. Business policies provided below.
                    2. Database results provided by the system in <sql_response> tags when the question requires data.

                    <business_policies>
                    {BUSINESS_POLICIES}
                    </business_policies>

                    <rules>
                    <rule>If the question can be answered from the business policies alone, answer directly from them.</rule>
                    <rule>If the database results are relevant, use them to complement or support your answer.</rule>
                    <rule>If the database results are empty, answer based only on the business policies.</rule>
                    <rule>Always respond in the same language the user used.</rule>
                    <rule>Never mention SQL, tables, column names, or internal system details in your response.</rule>
                    <rule>If you cannot find enough information to answer, tell the user to contact the customer service team:
                        - Phone: (+57) 315 622 40 81
                        - Address: Cl. 5a #79-93 a 79-1, Buenaventura, Valle del Cauca
                        - Postal code: 764501
                    </rule>
                    </rules>
                    """
            ),
        )

        session_store[session_id] = {
            "sql": sql_chat,
            "answer": answer_chat,
            "last_activity": now,
        }
    else:
        session_store[session_id]["last_activity"] = now

    return session_store[session_id]


def clear_session(session_id: str):
    session_store.pop(session_id, None)


async def send_with_retry(chat, prompt: str, config=None, retries=2):
    for i in range(retries):
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: chat.send_message(prompt, config=config)
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 10 * (2**i)
                print(f"Rate limit, esperando {wait}s... intento {i+1}")
                await asyncio.sleep(wait)
            else:
                raise e
    raise Exception("Máximo de reintentos alcanzado")


def query(sql_query: str):
    with engine.connect() as connection:
        result = connection.execute(text(sql_query))
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


async def human_query_to_sql(
    human_query: str, session_id: str
):

    chats = await get_or_create_session(session_id)

    chat = chats["sql"]

    prompt = f"""
            <human_query>
            {human_query}
            </human_query>
            """
    config = GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ResponseLLM,
    )
    
    response = await send_with_retry(chat, prompt, config=config)
    print("LLM response:", response)
    llm_response = ResponseLLM.model_validate_json(response)
    print("SQL model response:", llm_response.model_dump())

    return llm_response.model_dump()


async def build_answer(
    result: list[dict[str, Any]],
    human_query: str,
    session_id: str,
) -> str:

    chats = await get_or_create_session(session_id)

    chat = chats["answer"]

    prompt = f"""
        
        <user_question>
        {human_query}
        </user_question>

        <sql_response>
        {result}
        </sql_response>
        """

    response = await send_with_retry(chat, prompt)
    print("Answer model response:", response)

    return response


async def _run_query(
    human_query: str,
    session_id: str,
):

    try:
        sql_query = await human_query_to_sql(human_query, session_id)
        result = query(sql_query["sql_query"])
    except Exception:
        result = []

    print(result)
    try:
        answer = await build_answer(result, human_query, session_id)
    
    except Exception as e:
        print(f'error:{str(e)}')
        answer= "En este momento no puedo responder, por favor intentalo mas tarde"

    return {"answer": answer}
