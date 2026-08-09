const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * POSTs the conversation and streams back SSE events. fetch + a manual
 * reader is used instead of EventSource because EventSource can't send a
 * POST body, and the whole message history has to go up on every call
 * since the backend is intentionally stateless (see architecture doc).
 */
export async function streamChat(messages, handlers, signal) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError?.(`Request failed with status ${res.status}`);
    handlers.onDone?.();
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      let event = "message";
      let dataStr = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }

      let data = null;
      try {
        data = dataStr ? JSON.parse(dataStr) : null;
      } catch {
        data = dataStr;
      }

      if (event === "token") handlers.onToken?.(data);
      else if (event === "tool_call") handlers.onToolCall?.(data);
      else if (event === "tool_result") handlers.onToolResult?.(data);
      else if (event === "error") handlers.onError?.(data?.message ?? "Unknown error");
      else if (event === "done") handlers.onDone?.();
    }
  }
}
