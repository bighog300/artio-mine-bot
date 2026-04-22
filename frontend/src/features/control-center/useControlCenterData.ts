import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getActivityFeed, getJobs, getOperationalMetrics, getQueues, getSources, getStats } from "@/lib/api";

interface ControlAction {
  id: string;
  title: string;
  description: string;
  status: "ready" | "attention";
  confidence: number;
  href: string;
}

export function useControlCenterData() {
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const metricsQuery = useQuery({ queryKey: ["operational-metrics"], queryFn: getOperationalMetrics });
  const jobsQuery = useQuery({ queryKey: ["jobs", "dashboard"], queryFn: () => getJobs({ limit: 200 }) });
  const queuesQuery = useQuery({ queryKey: ["queues"], queryFn: getQueues });
  const activityQuery = useQuery({
    queryKey: ["activity-feed"],
    queryFn: () => getActivityFeed({ limit: 20 }),
    refetchInterval: (query) => (query.state.status === "success" ? 10_000 : false),
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });

  const successRate = useMemo(() => {
    const all = jobsQuery.data?.items ?? [];
    if (!all.length) return 0;
    return Math.round((all.filter((job) => job.status === "completed").length / all.length) * 100);
  }, [jobsQuery.data]);

  const prioritizedActions = useMemo<ControlAction[]>(() => {
    const pendingReview = statsQuery.data?.records.pending ?? 0;
    const failedJobs = jobsQuery.data?.items.filter((job) => job.status === "failed").length ?? 0;
    const pausedQueues = queuesQuery.data?.items.reduce((acc, q) => acc + q.paused, 0) ?? 0;

    return [
      {
        id: "review",
        title: "Review pending records",
        description: `${pendingReview} records are waiting for moderation before export.`,
        status: pendingReview > 0 ? "attention" : "ready",
        confidence: pendingReview === 0 ? 96 : Math.max(40, 90 - pendingReview),
        href: "/admin-review",
      },
      {
        id: "jobs",
        title: "Resolve failed jobs",
        description: failedJobs > 0 ? `${failedJobs} jobs need retry or intervention.` : "No failed jobs detected.",
        status: failedJobs > 0 ? "attention" : "ready",
        confidence: failedJobs === 0 ? 98 : Math.max(35, 90 - failedJobs * 8),
        href: "/jobs",
      },
      {
        id: "queues",
        title: "Inspect paused queues",
        description: pausedQueues > 0 ? `${pausedQueues} queue workers are paused.` : "All queues are active.",
        status: pausedQueues > 0 ? "attention" : "ready",
        confidence: pausedQueues === 0 ? 95 : Math.max(30, 88 - pausedQueues * 12),
        href: "/queues",
      },
    ];
  }, [jobsQuery.data, queuesQuery.data, statsQuery.data]);

  return {
    statsQuery,
    sourcesQuery,
    metricsQuery,
    jobsQuery,
    queuesQuery,
    activityQuery,
    successRate,
    prioritizedActions,
  };
}
