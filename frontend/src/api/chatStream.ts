import type { StreamEvent } from "../types";

interface ChatPayload {
  message: string;
  user_id: string;
  thread_id?: string;
}

function parseEvent(block: string): StreamEvent | null {
  const lines = block.split(/\r?\n/);
  const type = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!type || !data) return null;
  return { type, data: JSON.parse(data) } as StreamEvent;
}

export async function streamChat(
  payload: ChatPayload,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    blocks.forEach((block) => {
      const event = parseEvent(block);
      if (event) onEvent(event);
    });
    if (done) break;
  }
}
