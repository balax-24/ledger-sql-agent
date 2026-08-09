import { useCallback, useRef, useState } from "react";
import { streamChat } from "../api/chatStream.js";

let uid = 0;
const nextId = () => `${Date.now()}-${uid++}`;

/**
 * `turns` is the rich, UI-facing conversation (text + tool/chart/mermaid
 * blocks, streaming status). Only the plain {role, content} text gets sent
 * back to the backend as history — see chatStream.js and the architecture
 * doc for why tool-call mechanics from past turns aren't resent.
 */
export function useChatStream() {
  const [turns, setTurns] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const pendingArgsRef = useRef({});
  const abortRef = useRef(null);

  const updateLastAssistant = useCallback((updater) => {
    setTurns((prev) => {
      const next = [...prev];
      const lastIdx = next.length - 1;
      next[lastIdx] = updater(next[lastIdx]);
      return next;
    });
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      const historyForBackend = turns.map((t) => ({ role: t.role, content: t.text }));
      historyForBackend.push({ role: "user", content: trimmed });

      setTurns((prev) => [
        ...prev,
        { id: nextId(), role: "user", text: trimmed, blocks: [] },
        { id: nextId(), role: "assistant", text: "", blocks: [], streaming: true, error: null },
      ]);
      setIsStreaming(true);
      pendingArgsRef.current = {};

      const controller = new AbortController();
      abortRef.current = controller;

      await streamChat(
        historyForBackend,
        {
          onToolCall: ({ name, args }) => {
            pendingArgsRef.current[name] = args;
            updateLastAssistant((turn) => ({
              ...turn,
              blocks: [
                ...turn.blocks,
                { id: nextId(), type: "tool", name, args, status: "running", result: null },
              ],
            }));
          },
          onToolResult: ({ name, result, visible }) => {
            updateLastAssistant((turn) => {
              const blocks = [...turn.blocks];
              for (let i = blocks.length - 1; i >= 0; i--) {
                if (blocks[i].type === "tool" && blocks[i].name === name && blocks[i].status === "running") {
                  blocks[i] = {
                    ...blocks[i],
                    status: result?.success ? "done" : "error",
                    result,
                  };
                  break;
                }
              }
              if (visible && result?.success) {
                if (name === "generate_chart") {
                  blocks.push({ id: nextId(), type: "chart", spec: result.spec });
                } else if (name === "generate_er_diagram") {
                  blocks.push({ id: nextId(), type: "mermaid", kind: "er", mermaid: result.mermaid, title: "Entity relationships" });
                } else if (name === "generate_flowchart") {
                  blocks.push({ id: nextId(), type: "mermaid", kind: "flow", mermaid: result.mermaid, title: result.title });
                } else if (name === "explain_data") {
                  blocks.push({ id: nextId(), type: "explanation", explanation: result.explanation });
                }
              }
              return { ...turn, blocks };
            });
          },

          onToken: (chunk) => {
            updateLastAssistant((turn) => ({ ...turn, text: turn.text + chunk }));
          },
          onError: (message) => {
            updateLastAssistant((turn) => ({ ...turn, error: message }));
          },
          onDone: () => {
            updateLastAssistant((turn) => ({ ...turn, streaming: false }));
            setIsStreaming(false);
          },
        },
        controller.signal
      ).catch(() => {
        updateLastAssistant((turn) => ({ ...turn, streaming: false, error: "Connection lost." }));
        setIsStreaming(false);
      });
    },
    [turns, isStreaming, updateLastAssistant]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { turns, isStreaming, sendMessage, stop };
}
