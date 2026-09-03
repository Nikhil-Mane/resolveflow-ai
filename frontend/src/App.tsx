import { FormEvent, useEffect, useRef, useState } from "react";
import { streamChat } from "./api/chatStream";
import { ChatMessage } from "./components/ChatMessage";
import { ToolStatus } from "./components/ToolStatus";
import type { ChatMessage as Message, StreamEvent } from "./types";
import "./styles.css";

const savedMessages = (): Message[] => {
  try { return JSON.parse(localStorage.getItem("resolveflow_messages") ?? "[]"); }
  catch { return []; }
};

export default function App() {
  const [userId, setUserId] = useState(localStorage.getItem("resolveflow_user") ?? "customer-101");
  const [threadId, setThreadId] = useState(localStorage.getItem("resolveflow_thread") ?? "");
  const [messages, setMessages] = useState<Message[]>(savedMessages);
  const [tools, setTools] = useState<Record<string, string>>({});
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    localStorage.setItem("resolveflow_messages", JSON.stringify(messages));
  }, [messages]);

  const updateAssistant = (id: string, text: string, status?: Message["status"]) =>
    setMessages((items) => items.map((item) => item.id === id
      ? { ...item, content: item.content + text, status: status ?? item.status }
      : item));

  const handleEvent = (event: StreamEvent, assistantId: string) => {
    if (event.type === "session") {
      const id = String(event.data.thread_id);
      setThreadId(id);
      localStorage.setItem("resolveflow_thread", id);
    } else if (event.type === "tool_start" || event.type === "tool_end") {
      setTools((current) => ({ ...current, [String(event.data.name)]: event.type === "tool_start" ? "running" : "complete" }));
    } else if (event.type === "token") {
      updateAssistant(assistantId, String(event.data.text));
    } else if (event.type === "done") {
      updateAssistant(assistantId, "", "complete");
    } else if (event.type === "error") {
      throw new Error(String(event.data.message));
    }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || !userId.trim() || streaming) return;

    const assistantId = crypto.randomUUID();
    setMessages((items) => [...items,
      { id: crypto.randomUUID(), role: "user", content: text },
      { id: assistantId, role: "assistant", content: "", status: "streaming" },
    ]);
    setInput(""); setTools({}); setError(""); setStreaming(true);
    localStorage.setItem("resolveflow_user", userId.trim());
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat({ message: text, user_id: userId.trim(), thread_id: threadId || undefined },
        (item) => handleEvent(item, assistantId), controller.signal);
    } catch (caught) {
      const stopped = caught instanceof DOMException && caught.name === "AbortError";
      updateAssistant(assistantId, stopped ? "" : " Unable to complete the request.", stopped ? "stopped" : "error");
      if (!stopped) setError(caught instanceof Error ? caught.message : "Request failed");
    } finally { setStreaming(false); abortRef.current = null; }
  };

  const newChat = () => {
    abortRef.current?.abort(); setMessages([]); setTools({}); setThreadId(""); setError("");
    localStorage.removeItem("resolveflow_thread");
    localStorage.removeItem("resolveflow_messages");
  };

  return (
    <main className="shell">
      <header><div><small>AI SUPPORT AGENT</small><h1>ResolveFlow</h1></div><b>{streaming ? "Working" : "Ready"}</b></header>
      <section className="session">
        <label>User ID<input value={userId} disabled={streaming} onChange={(e) => setUserId(e.target.value)} /></label>
        <span>Thread: {threadId || "New conversation"}</span>
        <button className="secondary" onClick={newChat}>New chat</button>
      </section>
      <section className="chat" aria-live="polite">
        {!messages.length && <div className="empty"><h2>How can I help?</h2><p>Ask about an order, policy, public API, or support hours.</p></div>}
        {messages.map((message) => <ChatMessage key={message.id} message={message} />)}
      </section>
      <ToolStatus tools={tools} />
      {error && <p className="error">{error}</p>}
      <form onSubmit={send}>
        <textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a support question..." rows={2} />
        {streaming ? <button type="button" className="stop" onClick={() => abortRef.current?.abort()}>Stop</button>
          : <button type="submit">Send</button>}
      </form>
    </main>
  );
}
