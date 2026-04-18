import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { cancelJob, getJob, getJobEvents, pauseJob, resumeJob, retryJob } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { JobProgressBar } from "@/components/jobs/JobProgressBar";
import { HeartbeatBadge } from "@/components/jobs/HeartbeatBadge";
import { JobEventTimeline } from "@/components/jobs/JobEventTimeline";
import { Button, Spinner } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";

export function JobDetail() {
  const isMobile = useIsMobile();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const [liveLines, setLiveLines] = useState<string[]>([]);
  const actionMutation = useMutation({
    mutationFn: async (action: "retry" | "pause" | "resume" | "cancel") => {
      if (action === "retry") return retryJob(id);
      if (action === "pause") return pauseJob(id);
      if (action === "resume") return resumeJob(id);
      return cancelJob(id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["job", id] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", id],
    queryFn: () => getJob(id),
    enabled: id.length > 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["running", "queued", "pending"].includes(status) ? 3000 : false;
    },
  });
  const { data: events } = useQuery({
    queryKey: ["job-events", id],
    queryFn: () => getJobEvents(id, { limit: 100 }),
    enabled: id.length > 0,
    refetchInterval: 3000,
  });

  useEffect(() => {
    const base = import.meta.env.VITE_API_URL || "/api";
    const stream = new EventSource(`${base.replace(/\/$/, "")}/logs/stream`);
    stream.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as Record<string, unknown>;
      if (parsed.stream_type !== "job_progress" || parsed.job_id !== id) return;
      const line = `[${new Date(String(parsed.timestamp)).toLocaleTimeString()}] ${String(parsed.stage ?? "stage")} | ${String(parsed.message ?? "")}`;
      setLiveLines((prev) => [...prev.slice(-199), line]);
    };
    return () => stream.close();
  }, [id]);

  if (isLoading || !job) {
    return <div className="text-sm text-muted-foreground">Loading job...</div>;
  }

  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h1 className="text-2xl lg:text-3xl font-bold">Job detail</h1>
        <Link to="/jobs" className="text-sm text-blue-600">← Back to Jobs</Link>
      </div>

      <div className="bg-card border rounded p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="font-semibold">{job.source ?? job.source_id}</div>
          <StatusBadge status={job.status} />
          <HeartbeatBadge job={job} />
          <span className="text-xs font-mono text-muted-foreground">{job.worker_id ?? "unassigned"}</span>
          <div className="grid grid-cols-2 sm:flex gap-2 w-full sm:w-auto">
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("retry")}>Retry</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("pause")}>Pause</Button>
            <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate("resume")}>Resume</Button>
            <Button fullWidth={isMobile} size="sm" variant="danger" onClick={() => actionMutation.mutate("cancel")}>Cancel</Button>
          </div>
        </div>
        {job.error_message && <div className="text-sm text-red-600">{job.error_message}</div>}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><div className="text-muted-foreground">Type</div><div>{job.job_type}</div></div>
          <div><div className="text-muted-foreground">Mode</div><div>{job.runtime_mode ?? "—"}</div></div>
          <div><div className="text-muted-foreground">Stage</div><div>{job.current_stage ?? "—"}</div></div>
          <div><div className="text-muted-foreground">Processed</div><div>{job.processed_count ?? 0}</div></div>
          <div><div className="text-muted-foreground">Failures</div><div>{job.failure_count ?? 0}</div></div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs text-muted-foreground">
          <div>Deterministic hits: <strong>{job.deterministic_hits ?? 0}</strong></div>
          <div>Deterministic misses: <strong>{job.deterministic_misses ?? 0}</strong></div>
          <div>Records created: <strong>{job.records_created ?? 0}</strong></div>
          <div>Records updated: <strong>{job.records_updated ?? 0}</strong></div>
          <div>Media assets captured: <strong>{job.media_assets_captured ?? 0}</strong></div>
          <div>Entity links created: <strong>{job.entity_links_created ?? 0}</strong></div>
        </div>
        <div>
          <div className="text-muted-foreground text-sm mb-1">Current item</div>
          <div className="text-sm break-all">{job.current_item ?? "—"}</div>
        </div>
        <JobProgressBar current={job.progress_current} total={job.progress_total} percent={job.progress_percent} />
        {job.last_log_message && <div className="text-xs text-muted-foreground">Latest: {job.last_log_message}</div>}
      </div>

      <div>
        <h2 className="font-semibold mb-2">Event timeline</h2>
        <JobEventTimeline items={events?.items ?? []} />
      </div>

      <div>
        <h2 className="font-semibold mb-2">Live console</h2>
        <pre className="bg-gray-900 text-green-300 text-xs p-3 rounded max-h-72 overflow-auto">
          {(liveLines.length ? liveLines : ["Waiting for job activity..."]).join("\n")}
        </pre>
      </div>
    </div>
  );
}
