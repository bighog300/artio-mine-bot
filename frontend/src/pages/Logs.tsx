import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Terminal, Trash2, Download } from "lucide-react";
import { deleteLogs, getLogs, getSources, type LogEntry } from "@/lib/api";

const LEVEL_COLORS: Record<string, string> = {
  error: "bg-red-100 text-red-700",
  warning: "bg-yellow-100 text-yellow-700",
  info: "bg-blue-100 text-blue-700",
  debug: "bg-gray-100 text-gray-700",
};

const ROW_HEIGHT = 44;
const TABLE_HEIGHT = 520;

function toCsv(logs: LogEntry[]): string {
  const esc = (value: unknown) => `"${String(value ?? "").split('"').join('""')}"`;
  const lines = ["timestamp,level,service,source_id,message,context"];
  for (const log of logs) {
    lines.push(
      [log.timestamp, log.level, log.service, log.source_id, log.message, log.context]
        .map(esc)
        .join(",")
    );
  }
  return lines.join("\n");
}

export function Logs() {
  const queryClient = useQueryClient();
  const [level, setLevel] = useState("");
  const [service, setService] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(100);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [streamOn, setStreamOn] = useState(true);
  const [streamLines, setStreamLines] = useState<LogEntry[]>([]);
  const [scrollTop, setScrollTop] = useState(0);

  const streamRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    setSkip(0);
  }, [level, service, sourceId, search, dateFrom, dateTo, limit]);

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const { data, isLoading } = useQuery({
    queryKey: ["logs", { level, service, sourceId, search, dateFrom, dateTo, skip, limit }],
    queryFn: () =>
      getLogs({
        level: level || undefined,
        service: service || undefined,
        source_id: sourceId || undefined,
        search: search || undefined,
        date_from: dateFrom ? new Date(`${dateFrom}T00:00:00Z`).toISOString() : undefined,
        date_to: dateTo ? new Date(`${dateTo}T23:59:59Z`).toISOString() : undefined,
        skip,
        limit,
      }),
    refetchInterval: autoRefresh ? 5000 : false,
  });

  useEffect(() => {
    if (!streamOn) {
      return;
    }

    const base = import.meta.env.VITE_API_URL || "/api";
    const url = `${base.replace(/\/$/, "")}/logs/stream`;
    const source = new EventSource(url);

    source.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as LogEntry;
      setStreamLines((prev) => [...prev.slice(-199), parsed]);
      queryClient.invalidateQueries({ queryKey: ["logs"] });
    };

    return () => source.close();
  }, [streamOn, queryClient]);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamLines]);

  const deleteMutation = useMutation({
    mutationFn: ({ days, levelFilter }: { days: number; levelFilter?: string }) =>
      deleteLogs(days, levelFilter),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["logs"] });
    },
  });

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;

  const startIndex = Math.floor(scrollTop / ROW_HEIGHT);
  const visibleCount = Math.ceil(TABLE_HEIGHT / ROW_HEIGHT) + 8;
  const visibleItems = useMemo(
    () => logs.slice(startIndex, startIndex + visibleCount),
    [logs, startIndex, visibleCount]
  );

  const exportLogs = (format: "json" | "csv") => {
    const blob =
      format === "json"
        ? new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" })
        : new Blob([toCsv(logs)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `logs-${Date.now()}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Logs</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => exportLogs("json")}
            className="flex items-center gap-2 px-3 py-2 border rounded-md bg-white hover:bg-gray-50 text-sm"
          >
            <Download size={16} /> Export JSON
          </button>
          <button
            onClick={() => exportLogs("csv")}
            className="flex items-center gap-2 px-3 py-2 border rounded-md bg-white hover:bg-gray-50 text-sm"
          >
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-3 space-y-3">
        <div className="flex flex-wrap gap-2">
          <select value={level} onChange={(e) => setLevel(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">All Levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
          <select value={service} onChange={(e) => setService(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">All Services</option>
            <option value="api">API</option>
            <option value="worker">Worker</option>
          </select>
          <select value={sourceId} onChange={(e) => setSourceId(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">All Sources</option>
            {sources?.items.map((s) => (
              <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
            ))}
          </select>
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search logs"
            className="border rounded px-2 py-1.5 text-sm min-w-52"
          />
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded px-2 py-1.5 text-sm" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded px-2 py-1.5 text-sm" />
          <label className="inline-flex items-center gap-2 text-sm px-2">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Auto-refresh (5s)
          </label>
          <button
            onClick={() => {
              const answer = prompt("Delete logs older than days (7 / 30 / 90 / all)", "30");
              if (!answer) return;
              const value = answer.toLowerCase() === "all" ? 0 : Number(answer);
              if (Number.isNaN(value)) return;
              if (confirm("Are you sure you want to delete logs?")) {
                deleteMutation.mutate({ days: value, levelFilter: level || undefined });
              }
            }}
            className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded hover:bg-red-50 text-red-700"
          >
            <Trash2 size={16} /> Clear Logs
          </button>
        </div>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="grid grid-cols-6 bg-gray-50 text-xs font-semibold uppercase text-gray-600 sticky top-0 z-10">
          {['Timestamp', 'Level', 'Service', 'Source', 'Message', 'Context'].map((c) => (
            <div key={c} className="p-3 border-b">{c}</div>
          ))}
        </div>
        <div
          style={{ height: TABLE_HEIGHT }}
          className="overflow-auto"
          onScroll={(e) => setScrollTop((e.target as HTMLDivElement).scrollTop)}
        >
          <div style={{ height: logs.length * ROW_HEIGHT, position: "relative" }}>
            {visibleItems.map((log, idx) => {
              const realIndex = startIndex + idx;
              const top = realIndex * ROW_HEIGHT;
              return (
                <div key={log.id} style={{ position: "absolute", top, left: 0, right: 0 }}>
                  <button
                    onClick={() => setExpandedRows((p) => ({ ...p, [log.id]: !p[log.id] }))}
                    className="grid grid-cols-6 w-full text-left text-sm hover:bg-gray-50 border-b"
                  >
                    <div className="p-3 truncate">{new Date(log.timestamp).toLocaleString()}</div>
                    <div className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${LEVEL_COLORS[log.level] ?? LEVEL_COLORS.info}`}>
                        {log.level.toUpperCase()}
                      </span>
                    </div>
                    <div className="p-3 uppercase text-xs">{log.service}</div>
                    <div className="p-3 truncate text-xs text-gray-500">{log.source_id ?? "—"}</div>
                    <div className="p-3 truncate">{log.message}</div>
                    <div className="p-3 truncate text-xs text-gray-500">{log.context ?? "—"}</div>
                  </button>
                  {expandedRows[log.id] && (
                    <pre className="bg-gray-900 text-green-400 font-mono text-sm p-3 overflow-auto border-b">
                      {JSON.stringify(log.context ? JSON.parse(log.context) : {}, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
          {!isLoading && logs.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <p className="font-medium">No logs found</p>
              <p className="text-sm">Try adjusting filters or date range.</p>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">Showing {Math.min(skip + 1, total)}–{Math.min(skip + limit, total)} of {total}</div>
        <div className="flex items-center gap-2">
          <select value={String(limit)} onChange={(e) => setLimit(Number(e.target.value))} className="border rounded px-2 py-1.5 text-sm">
            {[25, 50, 100, 500].map((size) => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
          <button onClick={() => setSkip(Math.max(0, skip - limit))} disabled={skip === 0} className="px-3 py-1.5 border rounded disabled:opacity-50 text-sm">Previous</button>
          <button onClick={() => setSkip(skip + limit)} disabled={skip + limit >= total} className="px-3 py-1.5 border rounded disabled:opacity-50 text-sm">Next</button>
        </div>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        <button
          onClick={() => setStreamOn((v) => !v)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium border-b bg-gray-50 hover:bg-gray-100"
        >
          <Terminal size={16} /> Live Stream {streamOn ? "ON" : "OFF"}
        </button>
        <div ref={streamRef} className="max-h-64 overflow-auto bg-gray-900 text-green-400 font-mono text-sm p-3 space-y-1">
          {streamLines.slice(-200).map((line, i) => (
            <div key={`${line.timestamp}-${i}`} className={line.level === "error" ? "text-red-400" : line.level === "warning" ? "text-yellow-400" : line.level === "info" ? "text-blue-300" : "text-gray-300"}>
              [{new Date(line.timestamp).toLocaleTimeString()}] {line.level.toUpperCase()} {line.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
