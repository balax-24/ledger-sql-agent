import React from "react";

export default function ExplanationCard({ explanation }) {
  return (
    <div className="my-2 w-full rounded-xl border border-border bg-surface p-4 animate-fade-in shadow-sm">
      <div className="mb-2.5 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-good animate-pulse" />
        <h4 className="font-display text-sm font-medium text-ink-primary">Data Insights & Explanation</h4>
      </div>
      <div className="text-ink-secondary text-sm leading-relaxed whitespace-pre-wrap font-sans">
        {explanation}
      </div>
    </div>
  );
}
