import { useState } from "react";
import { useChatStream } from "./hooks/useChatStream.js";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBar from "./components/InputBar.jsx";
import Sidebar from "./components/Sidebar.jsx";

export default function App() {
  const { turns, isStreaming, sendMessage, stop } = useChatStream();
  const [showSidebar, setShowSidebar] = useState(true);
  const [inputValue, setInputValue] = useState("");

  const handleInsertText = (text) => {
    setInputValue((prev) => (prev ? `${prev} ${text}` : text));
  };

  const handlePickSuggestion = (text) => {
    setInputValue("");
    sendMessage(text);
  };

  return (
    <div className="flex h-screen flex-col bg-base overflow-hidden">
      <header className="flex items-center justify-between border-b border-border px-5 py-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="font-display text-base font-semibold tracking-tight text-ink-primary">ledger</span>
            <span className="text-ink-muted">/</span>
            <span className="font-mono text-xs text-ink-secondary">db agent</span>
          </div>
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all ${
              showSidebar
                ? "border-accent bg-accent/10 text-accent"
                : "border-border bg-surface text-ink-secondary hover:text-ink-primary hover:border-accent/40"
            }`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h7" />
            </svg>
            <span className="hidden sm:inline">Schema Explorer</span>
          </button>
        </div>

        <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-good" />
          <span className="font-mono text-[11px] text-ink-secondary">sample_sales_db</span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          isOpen={showSidebar}
          onClose={() => setShowSidebar(false)}
          onInsertText={handleInsertText}
        />
        
        <div className="flex flex-1 flex-col min-w-0 bg-base">
          <main className="flex-1 overflow-y-auto">
            <ChatWindow turns={turns} onPickSuggestion={handlePickSuggestion} />
          </main>

          <InputBar
            onSend={sendMessage}
            disabled={isStreaming}
            onStop={stop}
            isStreaming={isStreaming}
            value={inputValue}
            setValue={setInputValue}
          />
        </div>
      </div>
    </div>
  );
}
