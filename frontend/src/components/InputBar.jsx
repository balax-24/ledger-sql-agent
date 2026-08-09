import { useState, useEffect } from "react";

export default function InputBar({ onSend, disabled, onStop, isStreaming, value, setValue }) {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);

  useEffect(() => {
    // Check for speech recognition support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = "en-US";

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
        }
      };

      rec.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      setRecognition(rec);
    }
  }, [setValue]);

  const toggleListening = () => {
    if (!recognition) return;
    if (isListening) {
      recognition.stop();
    } else {
      recognition.start();
    }
  };

  const submit = (e) => {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  };

  return (
    <form onSubmit={submit} className="border-t border-border bg-base px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-border bg-surface px-3 py-2 transition-colors focus-within:border-accent/50">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit(e);
            }
          }}
          rows={1}
          placeholder="Ask about your data…"
          className="max-h-32 flex-1 resize-none bg-transparent py-1.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none"
        />

        {recognition && (
          <button
            type="button"
            onClick={toggleListening}
            title={isListening ? "Stop listening" : "Ask with voice"}
            className={`shrink-0 rounded-lg p-1.5 transition-colors ${
              isListening
                ? "bg-bad/20 text-bad animate-pulse animate-blink"
                : "text-ink-muted hover:bg-raised hover:text-ink-primary"
            }`}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </button>
        )}

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="shrink-0 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-ink-secondary transition-colors hover:text-ink-primary"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className="shrink-0 rounded-lg bg-accent px-3.5 py-1.5 text-xs font-medium text-base disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        )}
      </div>
    </form>
  );
}
