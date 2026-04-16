import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Terminal, Trash2, Download } from "lucide-react";
import { deleteLogs, getLogs, getSources, type LogEntry } from "@/lib/api";
import { Badge, Button, Input, Select, Switch } from "@/components/ui";

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
  const [jobId, setJobId] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [stage, setStage] = useState("");
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
  }, [level, service, sourceId, search, jobId, workerId, stage, dateFrom, dateTo, limit]);

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const { data, isLoading } = useQuery({
    queryKey: ["logs", { level, service, sourceId, search, jobId, workerId, stage, dateFrom, dateTo, skip, limit }],
    queryFn: () =>
      getLogs({
        level: level || undefined,
        service: service || undefined,
        source_id: sourceId || undefined,
        search: search || undefined,
        job_id: jobId || undefined,
        worker_id: workerId || undefined,
        stage: stage || undefined,
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
          <Button
            onClick={() => exportLogs("json")}
            variant="secondary"
            icon={<Download size={16} />}
          >
            Export JSON
          </Button>
          <Button
            onClick={() => exportLogs("csv")}
            variant="secondary"
            icon={<Download size={16} />}
          >
            Export CSV
          </Button>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-3 space-y-3">
        <div className="flex flex-wrap gap-2">
          <Select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="min-w-40"
            options={[
              { value: "", label: "All Levels" },
              { value: "debug", label: "Debug" },
              { value: "info", label: "Info" },
              { value: "warning", label: "Warning" },
              { value: "error", label: "Error" },
            ]}
          />
          <Select
            value={service}
            onChange={(e) => setService(e.target.value)}
            className="min-w-40"
            options={[
              { value: "", label: "All Services" },
              { value: "api", label: "API" },
              { value: "worker", label: "Worker" },
            ]}
          />
          <Select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="min-w-56"
            options={[{ value: "", label: "All Sources" }, ...(sources?.items.map((s) => ({ value: s.id, label: s.name ?? s.url })) ?? [])]}
          />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search logs"
            className="min-w-52"
          />
          <Input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="job_id" className="min-w-36" />
          <Input value={workerId} onChange={(e) => setWorkerId(e.target.value)} placeholder="worker_id" className="min-w-36" />
          <Input value={stage} onChange={(e) => setStage(e.target.value)} placeholder="stage" className="min-w-28" />
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <div className="px-2">
            <Switch id="auto-refresh" label="Auto-refresh (5s)" checked={autoRefresh} onChange={setAutoRefresh} />
          </div>
          <Button
            onClick={() => {
              const answer = prompt("Delete logs older than days (7 / 30 / 90 / all)", "30");
              if (!answer) return;
              const value = answer.toLowerCase() === "all" ? 0 : Number(answer);
              if (Number.isNaN(value)) return;
              if (confirm("Are you sure you want to delete logs?")) {
                deleteMutation.mutate({ days: value, levelFilter: level || undefined });
              }
            }}
            variant="danger"
            icon={<Trash2 size={16} />}
          >
            Clear Logs
          </Button>
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
                      <Badge className={LEVEL_COLORS[log.level] ?? LEVEL_COLORS.info}>
                        {log.level.toUpperCase()}
                      </Badge>
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
          <Select
            value={String(limit)}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="w-24"
            options={[25, 50, 100, 500].map((size) => ({ value: String(size), label: String(size) }))}
          />
          <Button onClick={() => setSkip(Math.max(0, skip - limit))} disabled={skip === 0} variant="secondary" size="sm">Previous</Button>
          <Button onClick={() => setSkip(skip + limit)} disabled={skip + limit >= total} variant="secondary" size="sm">Next</Button>
        </div>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        <Button
          onClick={() => setStreamOn((v) => !v)}
          variant="secondary"
          className="h-auto w-full justify-start rounded-none border-b bg-gray-50 px-3 py-2"
          icon={<Terminal size={16} />}
        >
          Live Stream {streamOn ? "ON" : "OFF"}
        </Button>
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
