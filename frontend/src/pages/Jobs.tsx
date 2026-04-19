import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelJob, getJobs, pauseJob, resumeJob, retryJob } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { JobProgressBar } from "@/components/jobs/JobProgressBar";
import { HeartbeatBadge } from "@/components/jobs/HeartbeatBadge";
import { Link, useNavigate } from "react-router-dom";
import { ListChecks } from "lucide-react";
import { Button, EmptyState, Skeleton, SkeletonTableRows, useToast } from "@/components/ui";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { useIsMobile } from "@/lib/mobile-utils";

export function Jobs() {
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["jobs"], queryFn: () => getJobs({ limit: 200 }), refetchInterval: 5000 });

  const mutate = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: "retry" | "cancel" | "pause" | "resume" }) => {
      if (action === "retry") return retryJob(id);
      if (action === "cancel") return cancelJob(id);
      if (action === "pause") return pauseJob(id);
      return resumeJob(id);
    },
    onMutate: ({ action }) => toast.loading(`Job ${action} requested...`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Job action accepted");
    },
    onError: (error: Error) => toast.error("Job action failed", error.message),
  });

  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold">Jobs</h1>
      {isMobile ? (
        <div className="space-y-3">
          {isLoading && (
            <div className="space-y-3" role="status" aria-label="Loading jobs">
              {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-lg border" />)}
            </div>
          )}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <EmptyState
              icon={ListChecks}
              title="No jobs running"
              description="Start discovery or full mining from Sources to see queued and active jobs here."
              actionLabel="Go to Sources"
              onAction={() => navigate("/sources")}
            />
          )}
          {data?.items.map((job) => (
            <MobileCard key={job.id}>
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium text-sm truncate">{job.source ?? job.source_id}</div>
                <StatusBadge status={job.status} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <MobileCardRow label="Type" value={job.job_type} />
                <MobileCardRow label="Mode" value={job.runtime_mode ?? "—"} />
                <MobileCardRow label="Processed" value={job.processed_count ?? 0} />
                <MobileCardRow label="Failures" value={job.failure_count ?? 0} />
              </div>
              <JobProgressBar current={job.progress_current} total={job.progress_total} percent={job.progress_percent} />
              <div className="grid grid-cols-2 gap-2">
                <Link className="inline-flex h-10 items-center justify-center rounded-md bg-muted px-3 text-sm font-medium hover:bg-gray-200" to={`/jobs/${job.id}`}>Details</Link>
                <Button size="sm" variant="danger" onClick={() => mutate.mutate({ id: job.id, action: "cancel" })}>Cancel</Button>
              </div>
            </MobileCard>
          ))}
        </div>
      ) : (
        <div className="bg-card border rounded overflow-hidden">
          <table className="w-full text-sm block overflow-x-auto lg:table">
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
              {isLoading && <SkeletonTableRows columns={13} rows={4} />}
              {!isLoading && (data?.items.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={13} className="p-4">
                    <EmptyState
                      icon={ListChecks}
                      title="No jobs yet"
                      description="Run discovery or mining from the Sources page to start seeing pipeline activity and progress updates."
                    />
                  </td>
                </tr>
              )}
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
                    <JobProgressBar current={job.progress_current} total={job.progress_total} percent={job.progress_percent} />
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
      )}
    </div>
  );
}
