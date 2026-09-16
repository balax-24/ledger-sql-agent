import { useState, useEffect } from "react";

export default function InputBar({ onSend, disabled, onStop, isStreaming, value, setValue }) {
  const [isListening, setIsListening] = useState(false);
  const [hasSupport, setHasSupport] = useState(false);
  const [activeRecognition, setActiveRecognition] = useState(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setHasSupport(true);
    }
  }, []);

  const toggleListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    if (isListening) {
      if (activeRecognition) {
        activeRecognition.stop();
      }
      setIsListening(false);
    } else {
      try {
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
          if (event.error === "not-allowed") {
            alert("Microphone access denied. Please enable microphone permission in your browser settings to use voice input.");
          } else if (event.error === "no-speech") {
            console.log("No speech detected.");
          } else {
            alert(`Speech recognition error: ${event.error}`);
          }
        };

        rec.onend = () => {
          setIsListening(false);
          setActiveRecognition(null);
        };

        rec.start();
        setActiveRecognition(rec);
      } catch (err) {
        console.error("Failed to start speech recognition:", err);
        alert("Failed to initialize speech recognition.");
      }
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

        <button
          type="button"
          onClick={toggleListening}
          title={
            !hasSupport
              ? "Voice input is not supported in this browser"
              : isListening
              ? "Stop listening"
              : "Ask with voice"
          }
          aria-label={!hasSupport ? "Voice input not supported" : "Voice input"}
          className={`shrink-0 rounded-lg p-1.5 transition-colors ${
            !hasSupport
              ? "text-ink-muted/40 hover:text-ink-muted cursor-pointer"
              : isListening
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
