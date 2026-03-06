"use client";

import { useEffect, useMemo, useState } from "react";

type Msg = { role: "user" | "assistant"; content: string };

type StoredMemory = {
  id: number;
  category: string;
  text: string;
  action?: string;
};

type RetrievedMemory = {
  id: number;
  text: string;
  score: number;
};

type AllMemory = {
  id: number;
  category: string;
  text: string;
  created_at: string;
};

type ChatResponse = {
  reply: string;
  session_id: string;
  stored_memories?: StoredMemory[];
  retrieved_memories?: RetrievedMemory[];
};

export default function Home() {
  const [sessionId, setSessionId] = useState("balu");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [stored, setStored] = useState<StoredMemory[]>([]);
  const [retrieved, setRetrieved] = useState<RetrievedMemory[]>([]);
  const [allMemories, setAllMemories] = useState<AllMemory[]>([]);
  const [loading, setLoading] = useState(false);

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function loadMemories() {
    try {
      const res = await fetch(
        `${backendUrl}/long_memory?session_id=${encodeURIComponent(sessionId)}`
      );
      const data = await res.json();
      setAllMemories(data.memories || []);
    } catch (e) {
      console.error("Failed to load memories", e);
    }
  }

  useEffect(() => {
    loadMemories();
  }, [sessionId]);

  async function send() {
    const text = input.trim();
    if (!text) return;

    setLoading(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);

    try {
      const res = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      const data: ChatResponse = await res.json();

      setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      setStored(data.stored_memories ?? []);
      setRetrieved(data.retrieved_memories ?? []);
      await loadMemories();
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Error calling backend: ${String(e)}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function deleteMemory(memoryId: number) {
    try {
      const res = await fetch(`${backendUrl}/long_memory/${memoryId}`, {
        method: "DELETE",
      });

      const data = await res.json();

      if (data.ok || data.status === "deleted") {
        setRetrieved((prev) => prev.filter((m) => m.id !== memoryId));
        setStored((prev) => prev.filter((m) => m.id !== memoryId));
        await loadMemories();
      } else {
        alert("Failed to delete memory.");
      }
    } catch (e) {
      alert("Error deleting memory.");
    }
  }

  function clearChat() {
    setMessages([]);
    setStored([]);
    setRetrieved([]);
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">AI Memory Assistant</h1>
          <p className="mt-2 text-sm text-slate-600">
            Next.js UI → FastAPI → SQLite memories → embeddings → FAISS retrieval
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          {/* Left: Chat */}
          <section className="lg:col-span-2 rounded-2xl bg-white shadow-sm border border-slate-200 flex h-[78vh] flex-col">
            <div className="border-b border-slate-200 px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Chat</h2>
                <p className="text-xs text-slate-500">
                  Ask questions and watch memory retrieval happen in real time.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-600">Session</label>
                <input
                  className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  placeholder="balu"
                />
                <button
                  onClick={clearChat}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                >
                  Clear chat
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto bg-slate-50 px-4 py-4">
              {messages.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <div className="max-w-md text-center">
                    <div className="text-lg font-medium text-slate-700">
                      Start chatting with your memory assistant
                    </div>
                    <p className="mt-2 text-sm text-slate-500">
                      Try asking: “What is my favorite framework?” or update a memory like
                      “Actually my favorite framework is React now.”
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((m, idx) => (
                    <div
                      key={idx}
                      className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                          m.role === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-white border border-slate-200 text-slate-800"
                        }`}
                      >
                        <div className="mb-1 text-[11px] font-medium opacity-70">
                          {m.role === "user" ? "You" : "Assistant"}
                        </div>
                        <div>{m.content}</div>
                      </div>
                    </div>
                  ))}

                  {loading ? (
                    <div className="flex justify-start">
                      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                        Assistant is thinking…
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 px-4 py-4">
              <div className="flex gap-2">
                <input
                  className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your message..."
                  onKeyDown={(e) => {
                    if (e.key === "Enter") send();
                  }}
                />
                <button
                  className={`rounded-xl px-5 py-3 text-sm font-medium text-white transition ${
                    canSend ? "bg-blue-600 hover:bg-blue-700" : "bg-blue-300"
                  }`}
                  onClick={send}
                  disabled={!canSend}
                >
                  {loading ? "Sending..." : "Send"}
                </button>
              </div>
            </div>
          </section>

          {/* Right: Memory panels */}
          <aside className="rounded-2xl bg-white shadow-sm border border-slate-200 h-[78vh] overflow-auto">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-lg font-semibold">Memory Dashboard</h2>
              <p className="text-xs text-slate-500">
                Retrieved, stored, and persistent memories for this session.
              </p>
            </div>

            <div className="space-y-6 p-4">
              <section>
                <h3 className="text-sm font-semibold text-slate-800">Retrieved memories</h3>
                <p className="mb-2 text-xs text-slate-500">Used by the assistant for this turn.</p>
                <div className="space-y-2">
                  {retrieved.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500">
                      No retrieved memories
                    </div>
                  ) : (
                    retrieved.map((m) => (
                      <div key={m.id} className="rounded-xl border border-slate-200 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-xs font-semibold text-slate-500">#{m.id}</div>
                            <div className="mt-1 text-sm text-slate-800">{m.text}</div>
                            <div className="mt-2 text-xs text-slate-500">
                              similarity score: {m.score.toFixed(2)}
                            </div>
                          </div>
                          <button
                            onClick={() => deleteMemory(m.id)}
                            className="rounded-lg bg-red-500 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-red-600"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-slate-800">Stored this turn</h3>
                <p className="mb-2 text-xs text-slate-500">
                  Newly added or updated memories from the latest message.
                </p>
                <div className="space-y-2">
                  {stored.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500">
                      No memories stored this turn
                    </div>
                  ) : (
                    stored.map((m) => (
                      <div key={m.id} className="rounded-xl border border-slate-200 p-3">
                        <div className="text-xs font-semibold text-slate-500">#{m.id}</div>
                        <div className="mt-1 text-sm text-slate-800">
                          [{m.category}] {m.text}
                        </div>
                        {m.action ? (
                          <div className="mt-2 text-xs text-slate-500">action: {m.action}</div>
                        ) : null}
                      </div>
                    ))
                  )}
                </div>
              </section>

              <section>
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">All memories</h3>
                    <p className="text-xs text-slate-500">Everything stored for this session.</p>
                  </div>
                  <button
                    onClick={loadMemories}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
                  >
                    Refresh
                  </button>
                </div>

                <div className="space-y-2">
                  {allMemories.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500">
                      No stored memories
                    </div>
                  ) : (
                    allMemories.map((m) => (
                      <div key={m.id} className="rounded-xl border border-slate-200 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-xs font-semibold text-slate-500">#{m.id}</div>
                            <div className="mt-1 text-sm text-slate-800">
                              [{m.category}] {m.text}
                            </div>
                            <div className="mt-2 text-xs text-slate-500">{m.created_at}</div>
                          </div>
                          <button
                            onClick={() => deleteMemory(m.id)}
                            className="rounded-lg bg-red-500 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-red-600"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}