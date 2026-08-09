import { useState } from "react";

const LABELS = {
  get_schema: { running: "Inspecting database schema…", done: "Inspected database schema" },
  execute_query: { running: "Running query…", done: "Ran query" },
  run_sql_query: { running: "Running query…", done: "Ran query" },
  generate_chart: { running: "Generating chart…", done: "Generated chart" },
  generate_er_diagram: { running: "Mapping table relationships…", done: "Generated ER diagram" },
  generate_flowchart: { running: "Building flowchart…", done: "Generated flowchart" },
};

export default function ToolActivity({ block }) {
  const [open, setOpen] = useState(false);
  const { name, args, status, result } = block;
  const label = LABELS[name]?.[status === "running" ? "running" : "done"] ?? name;
  const isSql = name === "execute_query" || name === "run_sql_query";

  const canExpand = isSql && status !== "running";

  return (
    <div className="my-1 font-mono text-xs">
      <button
        type="button"
        onClick={() => canExpand && setOpen((o) => !o)}
        className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors ${
          canExpand ? "cursor-pointer hover:bg-surface" : "cursor-default"
        }`}
      >
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
            status === "running" ? "animate-pulse bg-signal" : status === "error" ? "bg-bad" : "bg-good"
          }`}
        />
        <span className={status === "error" ? "text-bad" : "text-ink-secondary"}>
          {status === "error" ? result?.message ?? "Failed" : label}
        </span>
        {canExpand && <span className="ml-auto shrink-0 text-ink-muted">{open ? "hide sql" : "view sql"}</span>}
      </button>
      {open && canExpand && (
        <div className="ml-3.5 mt-1 space-y-1.5 rounded-md border border-border bg-raised p-3">
          <pre className="overflow-x-auto whitespace-pre-wrap text-signal">{result?.sql_executed ?? args?.sql}</pre>
          {result?.success && (
            <p className="text-ink-muted">
              {result.row_count} row{result.row_count === 1 ? "" : "s"} returned
              {result.truncated ? " (truncated)" : ""}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
