from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from db import (
    add_long_memory,
    clear_session,
    delete_long_memories_by_session,
    delete_long_memory,
    delete_message,
    fetch_recent_messages,
    find_latest_memory_by_category,
    init_db,
    list_long_memories,
    list_messages,
    long_memory_exists,
    save_message,
    update_long_memory,
)
from memory_extractor_llm import build_memory_extraction_prompt, parse_memory_json
from vector_memory import search_long_memories


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-memory-assistant-phi.vercel.app",
        "https://ai-memory-assistant-git-main-balasubramanyam507203s-projects.vercel.app",
        "https://ai-memory-assistant-qqfgdhl7o-balasubramanyam507203s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def embed_text(text: str) -> list[float]:
    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return emb.data[0].embedding


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class LongMemoryRequest(BaseModel):
    category: str = "preference"
    text: str
    session_id: str = "default"


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(request: ChatRequest):
    session_id = request.session_id
    user_message = request.message

    # 1) Save user message
    save_message(session_id=session_id, role="user", content=user_message)

    # 2) Extract long-term memories using LLM
    stored_memories = []

    extraction = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=build_memory_extraction_prompt(user_message),
    )

    raw = extraction.choices[0].message.content or "[]"

    try:
        extracted = parse_memory_json(raw)
    except Exception:
        extracted = []

    # 3) Fallback rule for obvious framework update phrases
    if not extracted:
        msg_l = user_message.lower()

        if (
            ("favorite framework" in msg_l or "favourite framework" in msg_l)
            and ("actually" in msg_l or "now" in msg_l)
            and " is " in msg_l
        ):
            framework = user_message.split(" is ", 1)[1].strip().strip(".")
            extracted = [
                {
                    "action": "update",
                    "category": "preference",
                    "text": f"Favorite framework is {framework}",
                }
            ]

    # 4) Store/update extracted memories
    for item in extracted:
        action = item["action"]
        category = item["category"]
        mem_text = item["text"]

        if action == "update":
            existing = find_latest_memory_by_category(session_id, category)

            if existing:
                emb = embed_text(mem_text)
                update_long_memory(existing["id"], category, mem_text, emb)
                stored_memories.append(
                    {
                        "id": existing["id"],
                        "category": category,
                        "text": mem_text,
                        "action": "updated",
                    }
                )
            else:
                if not long_memory_exists(
                    session_id=session_id,
                    category=category,
                    text=mem_text,
                ):
                    emb = embed_text(mem_text)
                    mem_id = add_long_memory(
                        session_id=session_id,
                        category=category,
                        text=mem_text,
                        embedding=emb,
                    )
                    stored_memories.append(
                        {
                            "id": mem_id,
                            "category": category,
                            "text": mem_text,
                            "action": "added",
                        }
                    )

        elif action == "add":
            if not long_memory_exists(
                session_id=session_id,
                category=category,
                text=mem_text,
            ):
                emb = embed_text(mem_text)
                mem_id = add_long_memory(
                    session_id=session_id,
                    category=category,
                    text=mem_text,
                    embedding=emb,
                )
                stored_memories.append(
                    {
                        "id": mem_id,
                        "category": category,
                        "text": mem_text,
                        "action": "added",
                    }
                )

    # 5) Fetch recent chat history
    history = fetch_recent_messages(session_id=session_id, limit=12)

    # 6) Retrieve relevant long-term memories
    long_hits = []
    try:
        q_emb = embed_text(user_message)
        long_hits = search_long_memories(
            session_id=session_id,
            query_embedding=q_emb,
            k=8,
        )
    except Exception:
        long_hits = []

    THRESHOLD = 0.30
    MAX_MEMORIES = 3

    filtered_memories = [h for h in long_hits if h.get("score", 0) >= THRESHOLD]
    filtered_memories = filtered_memories[:MAX_MEMORIES]

    long_memory_block = ""
    if filtered_memories:
        joined = "\n".join([f"- {h['text']}" for h in filtered_memories])
        long_memory_block = f"Long-term memories about the user:\n{joined}"

    # 7) Build system prompt
    system_msg = (
        "You are a helpful assistant.\n"
        "Use the chat history to stay consistent.\n"
        "If long-term memories are provided, treat them as true user facts."
    )
    if long_memory_block:
        system_msg += "\n\n" + long_memory_block

    # 8) Call OpenAI with system + history
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            *history,
        ],
    )

    reply = completion.choices[0].message.content or ""

    # 9) Save assistant reply
    save_message(session_id=session_id, role="assistant", content=reply)

    return {
        "reply": reply,
        "session_id": session_id,
        "stored_memories": stored_memories,
        "retrieved_memories": filtered_memories,
    }


@app.get("/memories")
def memories(session_id: str = "default", limit: int = 50):
    return {"session_id": session_id, "messages": list_messages(session_id, limit)}


@app.delete("/memories/{message_id}")
def forget_message(message_id: int):
    deleted = delete_message(message_id)
    if deleted == 0:
        return {"ok": False, "message": "Not found"}
    return {"ok": True, "deleted_id": message_id}


@app.delete("/sessions/{session_id}")
def reset_session(session_id: str):
    deleted_count = clear_session(session_id)
    return {
        "ok": True,
        "session_id": session_id,
        "deleted_messages": deleted_count,
    }


@app.post("/long_memory")
def create_long_memory(req: LongMemoryRequest):
    category = req.category.strip().lower()
    if category not in {"preference", "goal", "constraint"}:
        category = "preference"

    embedding = embed_text(req.text)
    memory_id = add_long_memory(
        session_id=req.session_id,
        category=category,
        text=req.text,
        embedding=embedding,
    )
    return {"ok": True, "id": memory_id, "session_id": req.session_id}


@app.get("/long_memory")
def get_long_memory(session_id: str = "default", limit: int = 100):
    return {"session_id": session_id, "memories": list_long_memories(session_id, limit)}


@app.delete("/long_memory/{memory_id}")
def remove_long_memory(memory_id: int):
    deleted = delete_long_memory(memory_id)
    if deleted == 0:
        return {"ok": False, "message": "Not found"}
    return {"ok": True, "deleted_id": memory_id}


@app.delete("/long_memory/session/{session_id}")
def forget_session_memories(session_id: str):
    deleted = delete_long_memories_by_session(session_id)
    return {
        "ok": True,
        "session_id": session_id,
        "deleted_count": deleted,
    }


@app.get("/long_memory/search")
def search_memory(session_id: str = "default", q: str = "", k: int = 5):
    if not q.strip():
        return {"session_id": session_id, "query": q, "results": []}

    q_emb = embed_text(q)
    results = search_long_memories(
        session_id=session_id,
        query_embedding=q_emb,
        k=k,
    )
    return {"session_id": session_id, "query": q, "results": results}