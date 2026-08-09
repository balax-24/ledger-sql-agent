const SUGGESTIONS = [
  "Show me the top 5 products by revenue this quarter",
  "Draw me the ER diagram for this database",
  "Create a flowchart showing how orders flow through our system",
  "Which region has the most customers?",
];

export default function EmptyState({ onPick }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg border border-accent/40 bg-accent-soft font-display text-lg text-accent">
        ⌁
      </div>
      <h2 className="font-display text-lg font-medium text-ink-primary">Ask your database anything</h2>
      <p className="mt-1.5 max-w-sm text-sm text-ink-secondary">
        No SQL required — describe what you want to know and I'll query it, chart it, or diagram it.
      </p>
      <div className="mt-6 grid w-full max-w-md gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-lg border border-border bg-surface px-3.5 py-2.5 text-left text-sm text-ink-secondary transition-colors hover:border-accent/40 hover:text-ink-primary"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
