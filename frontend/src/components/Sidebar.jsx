import { useState, useEffect } from "react";

export default function Sidebar({ isOpen, onClose, onInsertText }) {
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTables, setExpandedTables] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    async function fetchSchema() {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
        const res = await fetch(`${API_BASE}/api/schema`);
        if (!res.ok) throw new Error("Failed to load schema");
        const data = await res.json();
        if (data.success) {
          setSchema(data.tables);
          // Expand all tables by default initially
          const initialExpanded = {};
          data.tables.forEach((t) => {
            initialExpanded[t.name] = true;
          });
          setExpandedTables(initialExpanded);
        } else {
          throw new Error(data.message || "Unknown error");
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchSchema();
  }, []);

  const toggleTable = (tableName) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  if (!isOpen) return null;

  // Filter schema based on search query
  const filteredSchema = schema
    ? schema
        .map((table) => {
          const matchTable = table.name.toLowerCase().includes(searchQuery.toLowerCase());
          const matchingColumns = table.columns.filter((col) =>
            col.name.toLowerCase().includes(searchQuery.toLowerCase())
          );
          if (matchTable || matchingColumns.length > 0) {
            return {
              ...table,
              columns: matchingColumns.length > 0 ? table.columns : table.columns,
              isPartialMatch: !matchTable && matchingColumns.length > 0,
            };
          }
          return null;
        })
        .filter(Boolean)
    : [];

  return (
    <div className="flex h-full w-80 flex-col border-r border-border bg-surface font-sans text-sm animate-fade-in shrink-0">
      <div className="flex items-center justify-between border-b border-border p-4">
        <div className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-accent"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
            />
          </svg>
          <span className="font-display font-semibold tracking-tight text-ink-primary">Schema Explorer</span>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-ink-muted hover:bg-raised hover:text-ink-primary lg:hidden"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="p-3">
        <div className="relative">
          <input
            type="text"
            placeholder="Search tables or columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-border bg-base px-3 py-1.5 pl-8 text-xs text-ink-primary outline-none transition-colors focus:border-accent/50"
          />
          <svg
            className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-muted"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {loading && (
          <div className="flex flex-col items-center justify-center py-10 text-ink-muted">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <span className="mt-2 text-xs">Reading database metadata...</span>
          </div>
        )}

        {error && (
          <div className="rounded-md border border-bad/30 bg-bad/10 p-3 text-xs text-bad">
            Failed to load schema: {error}
          </div>
        )}

        {!loading && !error && filteredSchema.length === 0 && (
          <div className="py-8 text-center text-xs text-ink-muted">
            No tables or columns match "{searchQuery}"
          </div>
        )}

        {!loading &&
          !error &&
          filteredSchema.map((table) => {
            const isExpanded = !!expandedTables[table.name];
            return (
              <div key={table.name} className="mb-2 overflow-hidden rounded border border-border bg-base">
                <div
                  className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-raised transition-colors"
                  onClick={() => toggleTable(table.name)}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    <svg
                      className={`h-3 w-3 text-ink-muted transition-transform ${
                        isExpanded ? "rotate-90" : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="font-mono font-medium text-xs text-ink-primary truncate">
                      {table.name}
                    </span>
                    <span className="text-[10px] text-ink-muted shrink-0">
                      ({table.columns.length})
                    </span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleCopy(table.name, `t-${table.name}`)}
                      title="Copy table name"
                      className="rounded p-1 text-ink-muted hover:bg-base hover:text-ink-primary"
                    >
                      {copiedId === `t-${table.name}` ? (
                        <svg className="h-3.5 w-3.5 text-good" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                        </svg>
                      )}
                    </button>
                    <button
                      onClick={() => onInsertText(table.name)}
                      title="Insert to chat prompt"
                      className="rounded p-1 text-ink-muted hover:bg-base hover:text-accent"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                      </svg>
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-border bg-surface/50 px-3 py-1.5 divide-y divide-border/30">
                    {table.columns.map((col) => (
                      <div
                        key={col.name}
                        className="group flex items-center justify-between py-1.5 text-xs"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="font-mono text-ink-secondary truncate" title={col.name}>
                            {col.name}
                          </span>
                          <span className="font-mono text-[10px] text-accent/80 shrink-0">
                            {col.type}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleCopy(col.name, `c-${table.name}-${col.name}`)}
                            title="Copy column name"
                            className="rounded p-0.5 text-ink-muted hover:bg-raised hover:text-ink-primary"
                          >
                            {copiedId === `c-${table.name}-${col.name}` ? (
                              <svg className="h-3 w-3 text-good" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                              </svg>
                            )}
                          </button>
                          <button
                            onClick={() => onInsertText(col.name)}
                            title="Insert to chat prompt"
                            className="rounded p-0.5 text-ink-muted hover:bg-raised hover:text-accent"
                          >
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}
