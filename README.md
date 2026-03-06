# AI Memory Assistant

A full-stack AI assistant that remembers user preferences and goals using long-term semantic memory.

This project demonstrates how modern AI assistants maintain **persistent memory across conversations**.

---

# Features

- AI chat interface
- Long-term user memory
- Semantic memory retrieval using embeddings
- FAISS vector search
- Memory update & conflict resolution
- Memory dashboard in UI
- Delete and manage memories

---

# Tech Stack

## Frontend
- Next.js
- React
- Tailwind CSS

## Backend
- FastAPI
- Python
- OpenAI API
- SQLite
- FAISS
- Pydantic

---

# Architecture

```
User
 ↓
Next.js Frontend
 ↓
FastAPI Backend
 ↓
SQLite Memory Store
 ↓
OpenAI Embeddings
 ↓
FAISS Vector Search
 ↓
AI Response
```


---

# Example

User:


My favorite framework is React


Later:


Actually my favorite framework is Next.js now


Assistant stores and updates memory.

Later question:


What is my favorite framework?


Assistant correctly answers using stored memory.

---

# Local Setup

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

#Backend runs at:
http://127.0.0.1:8000

#Frontend
cd frontend
npm install
npm run dev

#Frontend runs at:
http://localhost:3000

#API Endpoints
Chat
POST /chat
List memories
GET /long_memory
Delete memory
DELETE /long_memory/{id}
Search memory
GET /long_memory/search

#Future Improvements
Streaming responses
Memory ranking improvements
User authentication
Cloud deployment
Memory evaluation benchmarks

#Author
Bala Subramanyam Pallapothu
Built as a GenAI Engineer portfolio project.