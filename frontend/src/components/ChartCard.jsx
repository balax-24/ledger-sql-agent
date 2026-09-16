import { useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const PALETTE = ["#C99B4A", "#4FB8AE", "#6FBE8F", "#E2685F", "#8B7FD1", "#6FA8D6"];
const axisStyle = { fontSize: 11, fill: "#9AA3B2", fontFamily: "'JetBrains Mono', monospace" };
const gridStroke = "#2C333F";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-raised px-3 py-2 text-xs font-mono text-ink-primary shadow-lg">
      {label !== undefined && <div className="mb-1 text-ink-secondary">{String(label)}</div>}
      {payload.map((p) => (
        <div key={p.dataKey}>
          {p.name ?? p.dataKey}: <span className="text-accent">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function ChartCard({ spec }) {
  const { chart_type, title, x_field, y_field, data } = spec;
  const [viewMode, setViewMode] = useState("chart"); // 'chart' | 'table'

  const hasData = Array.isArray(data) && data.length > 0;
  const columns = hasData ? Object.keys(data[0]) : [];

  // Check if y_field has plottable numeric data
  const hasValidNumericY = hasData && data.some((r) => {
    const val = r[y_field];
    return val !== null && val !== undefined && !isNaN(Number(val));
  });

  const chartId = "chart-" + title.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + Math.random().toString(36).substring(2, 8);

  const handleExportCSV = () => {
    if (!hasData) return;

    const headers = Object.keys(data[0]);
    const csvRows = [];

    // Header row
    csvRows.push(headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(","));

    // Data rows
    for (const row of data) {
      const values = headers.map((header) => {
        const val = row[header];
        if (val === null || val === undefined) return '""';
        const escaped = String(val).replace(/"/g, '""');
        return `"${escaped}"`;
      });
      csvRows.push(values.join(","));
    }

    // Prepend UTF-8 BOM so Excel displays international characters correctly
    const blob = new Blob(["\uFEFF" + csvRows.join("\r\n")], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_data.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportPNG = () => {
    const cardEl = document.getElementById(chartId);
    if (!cardEl) return;
    const svgEl = cardEl.querySelector("svg");
    if (!svgEl) return;

    const serializer = new XMLSerializer();
    let svgString = serializer.serializeToString(svgEl);

    if (!svgString.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      svgString = svgString.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }

    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const DOMURL = window.URL || window.webkitURL || window;
    const blobUrl = DOMURL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = svgEl.clientWidth || 600;
      canvas.height = svgEl.clientHeight || 320;
      const ctx = canvas.getContext("2d");

      ctx.fillStyle = "#121820";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      const pngUrl = canvas.toDataURL("image/png");
      const downloadLink = document.createElement("a");
      downloadLink.href = pngUrl;
      downloadLink.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_chart.png`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      DOMURL.revokeObjectURL(blobUrl);
    };
    img.src = blobUrl;
  };

  const showChart = viewMode === "chart" && hasValidNumericY;

  return (
    <div id={chartId} className="my-2.5 w-full rounded-xl border border-border bg-surface p-4 animate-fade-in shadow-sm relative group">
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-accent" />
          <h4 className="font-display text-sm font-medium text-ink-primary">{title}</h4>
          <span className="rounded bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-muted uppercase">
            {chart_type}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="flex rounded-md border border-border bg-raised p-0.5 text-[11px] font-mono">
            <button
              onClick={() => setViewMode("chart")}
              disabled={!hasValidNumericY}
              className={`px-2 py-0.5 rounded transition-colors ${
                viewMode === "chart" && hasValidNumericY
                  ? "bg-accent/20 text-accent font-medium"
                  : "text-ink-secondary hover:text-ink-primary disabled:opacity-30 disabled:cursor-not-allowed"
              }`}
            >
              Chart
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`px-2 py-0.5 rounded transition-colors ${
                viewMode === "table" || !hasValidNumericY
                  ? "bg-accent/20 text-accent font-medium"
                  : "text-ink-secondary hover:text-ink-primary"
              }`}
            >
              Table
            </button>
          </div>

          <button
            onClick={handleExportCSV}
            className="rounded px-2 py-1 text-[11px] font-mono bg-raised border border-border hover:border-accent hover:text-accent text-ink-secondary transition-colors cursor-pointer"
            title="Export data as CSV"
          >
            CSV
          </button>
          {showChart && (
            <button
              onClick={handleExportPNG}
              className="rounded px-2 py-1 text-[11px] font-mono bg-raised border border-border hover:border-accent hover:text-accent text-ink-secondary transition-colors cursor-pointer"
              title="Export chart as PNG"
            >
              PNG
            </button>
          )}
        </div>
      </div>

      {!hasValidNumericY && viewMode === "chart" && (
        <div className="mb-2 rounded border border-border/50 bg-raised px-3 py-1.5 text-xs text-ink-muted font-mono">
          Note: Field '{y_field}' is non-numeric; displaying tabular format instead.
        </div>
      )}

      {showChart ? (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {chart_type === "bar" ? (
              <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid stroke={gridStroke} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey={x_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <YAxis tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(201,155,74,0.08)" }} />
                <Bar dataKey={y_field} fill="#C99B4A" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : chart_type === "line" ? (
              <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid stroke={gridStroke} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey={x_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <YAxis tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Line type="monotone" dataKey={y_field} stroke="#4FB8AE" strokeWidth={2.5} dot={{ r: 3, fill: "#4FB8AE" }} />
              </LineChart>
            ) : chart_type === "pie" ? (
              <PieChart>
                <Tooltip content={<ChartTooltip />} />
                <Pie data={data} dataKey={y_field} nameKey={x_field} innerRadius={50} outerRadius={85} paddingAngle={2}>
                  {data.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="#1C222B" strokeWidth={2} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "Inter", color: "#9AA3B2" }} />
              </PieChart>
            ) : (
              <ScatterChart margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid stroke={gridStroke} strokeDasharray="3 3" />
                <XAxis dataKey={x_field} type="number" name={x_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <YAxis dataKey={y_field} type="number" name={y_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={data} fill="#C99B4A" />
              </ScatterChart>
            )}
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="max-h-64 overflow-auto rounded-lg border border-border/80 bg-raised/50">
          <table className="w-full text-left font-mono text-xs text-ink-secondary">
            <thead className="sticky top-0 border-b border-border bg-raised text-[11px] font-semibold text-ink-primary">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="px-3 py-2">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {data.slice(0, 100).map((row, idx) => (
                <tr key={idx} className="hover:bg-surface/50">
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-1.5 whitespace-nowrap">
                      {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-ink-muted italic">null</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
