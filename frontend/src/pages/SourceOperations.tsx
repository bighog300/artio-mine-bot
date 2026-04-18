import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  approveSourceModeratedAction,
  backfillSource,
  cancelActiveSourceRuns,
  getEnrichmentSummary,
  getSourceRuntimeMap,
  getSourceEvents,
  getSourceModeratedActions,
  getSourceOperations,
  getSourceRuns,
  pauseSourceRun,
  rejectSourceModeratedAction,
  resumeSourceRun,
  reprocessExistingPages,
  runDeterministicMine,
  runEnrichment,
  runSource,
  type Job,
  type SourceEvent,
} from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button, Select } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";

function formatConsoleLine(event: SourceEvent): string {
  const stage = event.stage ? `[${event.stage}]` : "";
  const worker = event.worker_id ? `(${event.worker_id})` : "";
  return `${new Date(event.timestamp).toLocaleTimeString()} ${event.level.toUpperCase()} ${stage} ${worker} ${event.message}`.replace(/\s+/g, " ").trim();
}

function RunRow({ run }: { run: Job }) {
  return (
    <tr className="border-t text-sm">
      <td className="p-2">{run.job_type}</td>
      <td className="p-2">{run.runtime_mode ?? "—"}</td>
      <td className="p-2"><StatusBadge status={run.status} /></td>
      <td className="p-2">{run.current_stage ?? "—"}</td>
      <td className="p-2">{run.progress_total ? `${run.progress_current ?? 0}/${run.progress_total}` : "—"}</td>
      <td className="p-2">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td>
      <td className="p-2">{run.duration_seconds ?? "—"}s</td>
    </tr>
  );
}

export function SourceOperations() {
  const isMobile = useIsMobile();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [consoleMode, setConsoleMode] = useState<"all" | "active" | "moderation">("all");

  const { data: ops } = useQuery({ queryKey: ["source-operations", id], queryFn: () => getSourceOperations(id!), enabled: !!id, refetchInterval: 5000 });
  const { data: runs } = useQuery({ queryKey: ["source-runs", id], queryFn: () => getSourceRuns(id!, { limit: 25 }), enabled: !!id, refetchInterval: 5000 });
  const { data: events } = useQuery({ queryKey: ["source-events", id], queryFn: () => getSourceEvents(id!, { limit: 200 }), enabled: !!id, refetchInterval: 3000 });
  const { data: runtimeMap } = useQuery({ queryKey: ["source-runtime-map", id], queryFn: () => getSourceRuntimeMap(id!), enabled: !!id });
  const { data: enrichmentSummary } = useQuery({ queryKey: ["source-enrichment-summary", id], queryFn: () => getEnrichmentSummary(id!), enabled: !!id, refetchInterval: 5000 });
  const { data: moderation } = useQuery({ queryKey: ["source-moderated-actions", id], queryFn: () => getSourceModeratedActions(id!, { status: "pending", limit: 100 }), enabled: !!id, refetchInterval: 5000 });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["source-operations", id] });
    queryClient.invalidateQueries({ queryKey: ["source-runs", id] });
    queryClient.invalidateQueries({ queryKey: ["source-events", id] });
    queryClient.invalidateQueries({ queryKey: ["source-moderated-actions", id] });
  };

  const actionMutation = useMutation({
    mutationFn: async (action: "run" | "deterministic" | "enrichment" | "reprocess" | "pause" | "resume" | "cancel" | "backfill") => {
      if (!id) return;
      if (action === "run") return runSource(id);
      if (action === "deterministic") return runDeterministicMine(id);
      if (action === "enrichment") return runEnrichment(id);
      if (action === "reprocess") return reprocessExistingPages(id);
      if (action === "pause") return pauseSourceRun(id);
      if (action === "resume") return resumeSourceRun(id);
      if (action === "cancel") return cancelActiveSourceRuns(id);
      return backfillSource(id);
    },
    onSuccess: refresh,
  });

  const moderationMutation = useMutation({
    mutationFn: async (payload: { actionId: string; decision: "approve" | "reject" }) => {
      if (!id) return;
      if (payload.decision === "approve") return approveSourceModeratedAction(id, payload.actionId);
      return rejectSourceModeratedAction(id, payload.actionId);
    },
    onSuccess: refresh,
  });

  useEffect(() => {
    if (!id) return;
    const base = import.meta.env.VITE_API_URL || "/api";
    const url = new URL(`${base.replace(/\/$/, "")}/logs/stream`, window.location.origin);
    url.searchParams.set("source_id", id);
    const stream = new EventSource(url.toString());
    stream.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ["source-events", id] });
      queryClient.invalidateQueries({ queryKey: ["source-runs", id] });
    };
    return () => stream.close();
  }, [id, queryClient]);

  const activeJobIds = useMemo(() => new Set((ops?.active_jobs ?? []).map((job) => job.id)), [ops?.active_jobs]);

  const consoleLines = useMemo(() => {
    const items = events?.items ?? [];
    return items.filter((event) => {
      if (consoleMode === "all") return true;
      if (consoleMode === "active") return activeJobIds.has(event.job_id);
      return event.event_type.includes("moder") || event.message.toLowerCase().includes("review");
    });
  }, [events?.items, consoleMode, activeJobIds]);

  if (!id) return <div className="p-6 text-red-500">Missing source id.</div>;

  return (
    <div className="space-y-4 lg:space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/sources/${id}`)} className="mb-1">← Source Detail</Button>
        <h1 className="text-2xl lg:text-3xl font-bold">Source Operations Console</h1>
        <p className="text-sm text-muted-foreground">{ops?.source?.name ?? ops?.source?.url ?? id}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-card border rounded p-4 space-y-3">
          <h2 className="font-semibold">Source Summary</h2>
          <div className="text-sm flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
            <StatusBadge status={ops?.source?.operational_status ?? ops?.source?.status ?? "unknown"} />
            <span>Active jobs: {ops?.active_jobs?.length ?? 0}</span>
            <span>Pending moderation: {ops?.pending_moderation_count ?? 0}</span>
            <span>Runtime map: {runtimeMap?.runtime_map_source ?? "none"}</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("run")}>Run</Button>
            <Button fullWidth={isMobile} size="sm" variant="primary" onClick={() => actionMutation.mutate("deterministic")}>Deterministic Mine</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("enrichment")}>Enrichment</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("reprocess")}>Reprocess Pages</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("pause")}>Pause</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("resume")}>Resume</Button>
            <Button fullWidth={isMobile} size="sm" variant="danger" onClick={() => actionMutation.mutate("cancel")}>Cancel Active</Button>
            <Button fullWidth={isMobile} size="sm" variant="primary" onClick={() => actionMutation.mutate("backfill")}>Backfill</Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground">
            <div>Runs: <strong>{enrichmentSummary?.runs ?? 0}</strong></div>
            <div>Records updated: <strong>{enrichmentSummary?.records_updated ?? 0}</strong></div>
            <div>Deterministic hits: <strong>{enrichmentSummary?.deterministic_hits ?? 0}</strong></div>
            <div>Deterministic misses: <strong>{enrichmentSummary?.deterministic_misses ?? 0}</strong></div>
            <div>Media captured: <strong>{enrichmentSummary?.media_assets_captured ?? 0}</strong></div>
            <div>Entity links: <strong>{enrichmentSummary?.entity_links_created ?? 0}</strong></div>
          </div>
        </div>

        <div className="bg-card border rounded p-4 space-y-3">
          <h2 className="font-semibold">Moderated Action Queue</h2>
          <div className="space-y-2 max-h-56 overflow-auto">
            {(moderation?.items ?? []).map((item) => (
              <div key={item.id} className="border rounded p-2 text-sm space-y-2">
                <div className="font-medium">Possible duplicate ({item.similarity_score ?? 0}%)</div>
                <div className="text-muted-foreground">{item.left_record?.title ?? item.left_record?.id} ↔ {item.right_record?.title ?? item.right_record?.id}</div>
                <div className="grid grid-cols-2 gap-2">
                  <Button fullWidth={isMobile} size="sm" variant="primary" onClick={() => moderationMutation.mutate({ actionId: item.id, decision: "approve" })}>Approve</Button>
                  <Button fullWidth={isMobile} size="sm" variant="danger" onClick={() => moderationMutation.mutate({ actionId: item.id, decision: "reject" })}>Reject</Button>
                </div>
              </div>
            ))}
            {(moderation?.items?.length ?? 0) === 0 && <p className="text-sm text-muted-foreground">No pending moderated actions.</p>}
          </div>
        </div>
      </div>

      <div className="bg-slate-950 text-green-300 rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-white">Live Console</h2>
          <Select
            className="w-44 text-xs text-black"
            value={consoleMode}
            onChange={(e) => setConsoleMode(e.target.value as "all" | "active" | "moderation")}
            options={[
              { value: "all", label: "Full source stream" },
              { value: "active", label: "Active job only" },
              { value: "moderation", label: "Moderation events" },
            ]}
          />
        </div>
        <div className="font-mono text-xs space-y-1 max-h-80 overflow-auto">
          {consoleLines.map((event) => (
            <div key={event.id}>{formatConsoleLine(event)}</div>
          ))}
        </div>
      </div>

      <div className="bg-card border rounded overflow-hidden">
        <div className="p-3 border-b font-semibold">Recent Run History</div>
        <table className="w-full block overflow-x-auto lg:table">
          <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="p-2 text-left">Type</th>
              <th className="p-2 text-left">Mode</th>
              <th className="p-2 text-left">Status</th>
              <th className="p-2 text-left">Stage</th>
              <th className="p-2 text-left">Progress</th>
              <th className="p-2 text-left">Started</th>
              <th className="p-2 text-left">Duration</th>
            </tr>
          </thead>
          <tbody>
            {(runs?.items ?? []).map((run) => <RunRow key={run.id} run={run} />)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
