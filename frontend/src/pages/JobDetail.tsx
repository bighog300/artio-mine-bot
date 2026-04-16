import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { cancelJob, getJob, getJobEvents, pauseJob, resumeJob, retryJob } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { JobProgressBar } from "@/components/jobs/JobProgressBar";
import { HeartbeatBadge } from "@/components/jobs/HeartbeatBadge";
import { JobEventTimeline } from "@/components/jobs/JobEventTimeline";
import { Button, Spinner } from "@/components/ui";

export function JobDetail() {
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
    return <div className="text-sm text-gray-500">Loading job...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Job detail</h1>
        <Link to="/jobs" className="text-sm text-blue-600">← Back to Jobs</Link>
      </div>

      <div className="bg-white border rounded p-4 space-y-3">
        <div className="flex gap-3 items-center">
          <div className="font-semibold">{job.source ?? job.source_id}</div>
          <StatusBadge status={job.status} />
          <HeartbeatBadge job={job} />
          <span className="text-xs font-mono text-gray-500">{job.worker_id ?? "unassigned"}</span>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("retry")}>Retry</Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("pause")}>Pause</Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("resume")}>Resume</Button>
          <Button size="sm" variant="danger" onClick={() => actionMutation.mutate("cancel")}>Cancel</Button>
        </div>
        {job.error_message && <div className="text-sm text-red-600">{job.error_message}</div>}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><div className="text-gray-500">Type</div><div>{job.job_type}</div></div>
          <div><div className="text-gray-500">Stage</div><div>{job.current_stage ?? "—"}</div></div>
          <div><div className="text-gray-500">Processed</div><div>{job.processed_count ?? 0}</div></div>
          <div><div className="text-gray-500">Failures</div><div>{job.failure_count ?? 0}</div></div>
        </div>
        <div>
          <div className="text-gray-500 text-sm mb-1">Current item</div>
          <div className="text-sm break-all">{job.current_item ?? "—"}</div>
        </div>
        <JobProgressBar current={job.progress_current} total={job.progress_total} percent={job.progress_percent} />
        {job.last_log_message && <div className="text-xs text-gray-600">Latest: {job.last_log_message}</div>}
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
