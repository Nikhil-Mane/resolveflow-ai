export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  status?: "streaming" | "complete" | "stopped" | "error";
}

export interface StreamEvent {
  type: "session" | "tool_start" | "tool_end" | "token" | "done" | "error";
  data: Record<string, unknown>;
}
