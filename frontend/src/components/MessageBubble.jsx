import ToolActivity from "./ToolActivity.jsx";
import ChartCard from "./ChartCard.jsx";
import MermaidCard from "./MermaidCard.jsx";
import ExplanationCard from "./ExplanationCard.jsx";

export default function MessageBubble({ turn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm border border-accent/30 bg-accent-soft px-4 py-2.5 text-sm text-ink-primary">
          {turn.text}
        </div>
      </div>
    );
  }

  const hasProse = turn.text || turn.streaming;

  return (
    <div className="flex justify-start animate-fade-in">
      <div className="w-full max-w-[85%]">
        {turn.blocks.map((block) => {
          if (block.type === "tool") return <ToolActivity key={block.id} block={block} />;
          if (block.type === "chart") return <ChartCard key={block.id} spec={block.spec} />;
          if (block.type === "explanation") return <ExplanationCard key={block.id} explanation={block.explanation} />;
          if (block.type === "mermaid")
            return <MermaidCard key={block.id} title={block.title} mermaid={block.mermaid} kind={block.kind} />;
          return null;
        })}

        {hasProse && (
          <div className="rounded-2xl rounded-tl-sm border border-border bg-raised px-4 py-2.5 text-sm leading-relaxed text-ink-primary">
            {turn.text}
            {turn.streaming && (
              <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-blink bg-accent align-text-bottom" />
            )}
          </div>
        )}
        {turn.error && <p className="mt-1.5 px-1 font-mono text-xs text-bad">⚠ {turn.error}</p>}
      </div>
    </div>
  );
}
