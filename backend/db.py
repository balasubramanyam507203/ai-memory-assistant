import sqlite3
from pathlib import Path
from typing import List, Dict

# Absolute path to backend/app.db (so it's always the same file)
DB_PATH = (Path(__file__).resolve().parent / "app.db").resolve()

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        # chat history table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        #long-term memory table (semantic memories)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS long_memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        try:
            conn.execute(
                "ALTER TABLE long_memories ADD COLUMS category TEXT NOT NULL DEFAULT 'preference'"
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()

    print(f" messages table ensured in DB: {DB_PATH}")

def save_message(session_id: str, role: str, content: str) -> None:
    # Safety: ensure table exists even if startup didn't run (or wrong DB was created)
    init_db()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()

def fetch_recent_messages(session_id: str, limit: int = 10) -> List[Dict[str, str]]:
    init_db()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    return [{"role": r["role"], "content": r["content"]} for r in rows][::-1]

def list_messages(session_id: str, limit: int = 50):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [dict(r) for r in rows][::-1]

def delete_message(message_id: int) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
        return cur.rowcount # 1 if deleted, 0 if not found
    
def clear_session(session_id: str) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        return cur.rowcount
    
import json
from typing import Optional

def add_long_memory(session_id: str, category: str, text: str, embedding: list[float]) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO long_memories (session_id, category, text, embedding_json) VALUES (?, ?, ?, ?)",
            (session_id, category, text, json.dumps(embedding),)
        )
        conn.commit()
        return int(cur.lastrowid)
    
def list_long_memories(session_id: str, limit: int = 100):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, category, text, created_at
            FROM long_memories
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [dict(r) for r in rows][::-1]

def delete_long_memory(memory_id: int) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM long_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cur.rowcount

def load_long_memories_with_embeddings(session_id: str):
    """Used for FAISS search: returns (ids, textx, embeddings)."""
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, category, text, embedding_json
            FROM long_memories
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchall()
    
    ids, texts, embs = [], [], []
    for r in rows:
        ids.append(int(r["id"]))
        texts.append(f"[{r['category']}] {r['text']}")
        embs.append(json.loads(r["embedding_json"]))
    return ids, texts, embs
        
def long_memory_exists(session_id: str, category: str, text: str) -> bool:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM long_memories WHERE session_id = ? AND category = ? AND LOWER(text) = LOWER(?) LIMIT 1",
            (session_id, category, text),
        ).fetchone()
    return row is not None      

def find_latest_memory_by_category(session_id: str, category: str):
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, category, text
            FROM long_memories
            WHERE session_id = ? AND category = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id, category),
        ).fetchone()
    return dict(row) if row else None

def update_long_memory(memory_id: int, category: str, text: str, embedding: list[float]) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE long_memories
            SET category = ?, text = ?, embedding_json = ?
            WHERE id = ?
            """,
            (category, text, json.dumps(embedding), memory_id),
        )
        conn.commit()
        return cur.rowcount
    
def delete_long_memory(memory_id: int) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM long_memories WHERE id = ?",
            (memory_id,),
        )
        conn.commit()
        return cur.rowcount
    
def delete_long_memories_by_session(session_id: str) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM long_memories WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
        return cur.rowcount
