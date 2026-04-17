import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelJob, getJobs, pauseJob, resumeJob, retryJob } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { JobProgressBar } from "@/components/jobs/JobProgressBar";
import { HeartbeatBadge } from "@/components/jobs/HeartbeatBadge";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui";

export function Jobs() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["jobs"], queryFn: () => getJobs({ limit: 200 }), refetchInterval: 5000 });
  const mutate = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "retry" | "cancel" | "pause" | "resume" }) => {
      if (action === "retry") return retryJob(id);
      if (action === "cancel") return cancelJob(id);
      if (action === "pause") return pauseJob(id);
      return resumeJob(id);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Jobs</h1>
      <div className="bg-card border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left p-3">Source</th>
              <th className="text-left p-3">Type</th>
              <th className="text-left p-3">Mode</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Worker</th>
              <th className="text-left p-3">Stage</th>
              <th className="text-left p-3">Current item</th>
              <th className="text-left p-3">Progress</th>
              <th className="text-left p-3">Timing</th>
              <th className="text-left p-3">Processed</th>
              <th className="text-left p-3">Failures</th>
              <th className="text-left p-3">Heartbeat</th>
              <th className="text-left p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={13} className="p-6 text-center text-muted-foreground/80">Loading...</td></tr>}
            {data?.items.map((job) => (
              <tr key={job.id} className="border-t">
                <td className="p-3">{job.source ?? job.source_id}</td>
                <td className="p-3">{job.job_type}</td>
                <td className="p-3 text-xs">{job.runtime_mode ?? "—"}</td>
                <td className="p-3"><StatusBadge status={job.status} /></td>
                <td className="p-3 text-xs font-mono">{job.worker_id ?? "—"}</td>
                <td className="p-3 text-xs">{job.current_stage ?? "—"}</td>
                <td className="p-3 text-xs max-w-52 truncate" title={job.current_item ?? ""}>{job.current_item ?? "—"}</td>
                <td className="p-3">
                  <JobProgressBar
                    current={job.progress_current}
                    total={job.progress_total}
                    percent={job.progress_percent}
                  />
                </td>
                <td className="p-3 text-xs text-muted-foreground">{job.duration_seconds ? `${job.duration_seconds}s` : "—"}</td>
                <td className="p-3">{job.processed_count ?? 0}</td>
                <td className="p-3">{job.failure_count ?? 0}</td>
                <td className="p-3"><HeartbeatBadge job={job} /></td>
                <td className="p-3">
                  <div className="flex gap-2 text-xs">
                    <Link className="inline-flex h-8 items-center justify-center rounded-md bg-muted px-3 text-sm font-medium hover:bg-gray-200" to={`/jobs/${job.id}`}>Details</Link>
                    <Button size="sm" variant="secondary" onClick={() => mutate.mutate({ id: job.id, action: "retry" })}>Retry</Button>
                    <Button size="sm" variant="secondary" onClick={() => mutate.mutate({ id: job.id, action: "pause" })}>Pause</Button>
                    <Button size="sm" variant="secondary" onClick={() => mutate.mutate({ id: job.id, action: "resume" })}>Resume</Button>
                    <Button size="sm" variant="danger" onClick={() => mutate.mutate({ id: job.id, action: "cancel" })}>Cancel</Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
