import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { getJob, getJobEvents } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { JobProgressBar } from "@/components/jobs/JobProgressBar";
import { HeartbeatBadge } from "@/components/jobs/HeartbeatBadge";
import { JobEventTimeline } from "@/components/jobs/JobEventTimeline";

export function JobDetail() {
  const { id = "" } = useParams();
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
    </div>
  );
}
