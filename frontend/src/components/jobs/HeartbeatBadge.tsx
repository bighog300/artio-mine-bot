import { Job } from "@/lib/api";

function minutesSince(iso?: string | null): number | null {
  if (!iso) return null;
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / 60000);
}

export function HeartbeatBadge({ job }: { job: Job }) {
  if (job.status === "paused") return <span className="px-2 py-0.5 rounded bg-yellow-100 text-yellow-700 text-xs">paused</span>;
  if (!["running", "queued", "pending"].includes(job.status)) {
    return <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground text-xs">terminal</span>;
  }
  if (job.is_stale) {
    const mins = minutesSince(job.last_heartbeat_at);
    return <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700 text-xs">stale{mins !== null ? ` ${mins}m` : ""}</span>;
  }
  return <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs">healthy</span>;
}
