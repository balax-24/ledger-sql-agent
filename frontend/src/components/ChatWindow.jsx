import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";
import EmptyState from "./EmptyState.jsx";

export default function ChatWindow({ turns, onPickSuggestion }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  if (turns.length === 0) {
    return <EmptyState onPick={onPickSuggestion} />;
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
      {turns.map((turn) => (
        <MessageBubble key={turn.id} turn={turn} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
