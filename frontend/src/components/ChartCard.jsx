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
const axisStyle = { fontSize: 12, fill: "#9AA3B2", fontFamily: "'JetBrains Mono', monospace" };
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

  const handleExportCSV = () => {
    if (!data || data.length === 0) return;
    
    // Extract headers
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Add header row
    csvRows.push(headers.join(","));
    
    // Add data rows
    for (const row of data) {
      const values = headers.map(header => {
        const val = row[header];
        const escaped = String(val).replace(/"/g, '""');
        return `"${escaped}"`;
      });
      csvRows.push(values.join(","));
    }
    
    // Create download link
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}_data.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const chartId = "chart-" + title.toLowerCase().replace(/[^a-z0-9]+/g, "-") + "-" + Math.random().toString(36).substring(2, 9);

  const handleExportPNG = () => {
    const cardEl = document.getElementById(chartId);
    if (!cardEl) return;
    const svgEl = cardEl.querySelector("svg");
    if (!svgEl) return;

    const serializer = new XMLSerializer();
    let svgString = serializer.serializeToString(svgEl);
    
    // Add explicitly standard attributes for compatibility
    if (!svgString.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
      svgString = svgString.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }
    
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const DOMURL = window.URL || window.webkitURL || window;
    const blobUrl = DOMURL.createObjectURL(svgBlob);
    
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = svgEl.clientWidth || 500;
      canvas.height = svgEl.clientHeight || 300;
      const ctx = canvas.getContext("2d");
      
      // Paint container bg color (dark slate matching dashboard theme)
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

  return (
    <div id={chartId} className="my-2 w-full rounded-xl border border-border bg-surface p-4 animate-fade-in shadow-sm relative group">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" />
          <h4 className="font-display text-sm font-medium text-ink-primary">{title}</h4>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExportCSV}
            className="rounded px-2 py-1 text-[10px] font-mono bg-raised border border-border hover:border-accent hover:text-accent text-ink-secondary transition-colors cursor-pointer"
            title="Export chart data to CSV"
          >
            export csv
          </button>
          <button
            onClick={handleExportPNG}
            className="rounded px-2 py-1 text-[10px] font-mono bg-raised border border-border hover:border-accent hover:text-accent text-ink-secondary transition-colors cursor-pointer"
            title="Export chart as PNG image"
          >
            export png
          </button>
        </div>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chart_type === "bar" ? (
            <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke={gridStroke} vertical={false} />
              <XAxis dataKey={x_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(201,155,74,0.08)" }} />
              <Bar dataKey={y_field} fill="#C99B4A" radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : chart_type === "line" ? (
            <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke={gridStroke} vertical={false} />
              <XAxis dataKey={x_field} tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={{ stroke: gridStroke }} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey={y_field} stroke="#4FB8AE" strokeWidth={2} dot={{ r: 3, fill: "#4FB8AE" }} />
            </LineChart>
          ) : chart_type === "pie" ? (
            <PieChart>
              <Tooltip content={<ChartTooltip />} />
              <Pie data={data} dataKey={y_field} nameKey={x_field} innerRadius={55} outerRadius={90} paddingAngle={2}>
                {data.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="#1C222B" strokeWidth={2} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "Inter", color: "#9AA3B2" }} />
            </PieChart>
          ) : (
            <ScatterChart margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke={gridStroke} />
              <XAxis
                dataKey={x_field}
                type="number"
                name={x_field}
                tick={axisStyle}
                axisLine={{ stroke: gridStroke }}
                tickLine={false}
              />
              <YAxis
                dataKey={y_field}
                type="number"
                name={y_field}
                tick={axisStyle}
                axisLine={{ stroke: gridStroke }}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: "3 3" }} />
              <Scatter data={data} fill="#C99B4A" />
            </ScatterChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
