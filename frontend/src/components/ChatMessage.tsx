import type { ChatMessage as Message } from "../types";

export function ChatMessage({ message }: { message: Message }) {
  return (
    <article className={`message ${message.role}`}>
      <span>{message.role === "user" ? "You" : "ResolveFlow"}</span>
      <p>{message.content || "Thinking..."}</p>
    </article>
  );
}
