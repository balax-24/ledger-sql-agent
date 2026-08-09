import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  themeVariables: {
    background: "#1C222B",
    primaryColor: "#242B36",
    primaryTextColor: "#EDEFF3",
    primaryBorderColor: "#2C333F",
    lineColor: "#4FB8AE",
    secondaryColor: "#3A3222",
    tertiaryColor: "#1C222B",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: "13px",
  },
});

let renderCount = 0;

export default function MermaidCard({ title, mermaid: code, kind }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const id = `mermaid-${kind}-${renderCount++}`;
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) containerRef.current.innerHTML = svg;
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message ?? "Could not render this diagram.");
      });
    return () => {
      cancelled = true;
    };
  }, [code, kind]);

  return (
    <div className="my-2 w-full overflow-x-auto rounded-xl border border-border bg-surface p-4 animate-fade-in">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-signal" />
        <h4 className="font-display text-sm font-medium text-ink-primary">{title}</h4>
      </div>
      {error ? (
        <p className="font-mono text-xs text-bad">⚠ {error}</p>
      ) : (
        <div ref={containerRef} className="flex justify-center [&_svg]:max-w-full" />
      )}
    </div>
  );
}
