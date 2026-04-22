import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getActivityFeed, getJobs, getOperationalMetrics, getQueues, getSources, getStats } from "@/lib/api";
import type { ControlCenterAction } from "@/features/control-center/types";

const LIVE_REFETCH_MS = 30_000;

const queryRefreshOptions = {
  refetchInterval: LIVE_REFETCH_MS,
  refetchOnWindowFocus: false,
} as const;

const severityValues: Record<ControlCenterAction["severity"], number> = {
  critical: 1,
  high: 0.7,
  medium: 0.4,
  low: 0.1,
};

const SEVERITY_WEIGHT = 40;
const IMPACT_WEIGHT = 30;
const CONFIDENCE_WEIGHT = 20;
const RECENCY_WEIGHT = 10;

function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

function computeFreshness(timestamp?: string | null): number {
  if (!timestamp) {
    return 0.2;
  }

  const ageMs = Date.now() - new Date(timestamp).getTime();
  if (Number.isNaN(ageMs) || ageMs < 0) {
    return 0;
  }

  const ageHours = ageMs / (1000 * 60 * 60);
  return clamp(1 - ageHours / 72);
}

function computePriorityScore(action: Omit<ControlCenterAction, "priorityScore">, freshness: number): number {
  const severityValue = severityValues[action.severity];
  const impactCount = action.impactCount ?? 0;
  const confidence = clamp(action.confidence ?? 0.5);

  return Number(
    (
      SEVERITY_WEIGHT * severityValue +
      IMPACT_WEIGHT * impactCount +
      CONFIDENCE_WEIGHT * (1 - confidence) +
      RECENCY_WEIGHT * freshness
    ).toFixed(2),
  );
}

function severityForCount(
  count: number,
  thresholds: { critical: number; high: number; medium: number },
): ControlCenterAction["severity"] {
  if (count >= thresholds.critical) return "critical";
  if (count >= thresholds.high) return "high";
  if (count >= thresholds.medium) return "medium";
  return "low";
}

export function useControlCenterData() {
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: getStats, ...queryRefreshOptions });
  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: getSources, ...queryRefreshOptions });
  const metricsQuery = useQuery({ queryKey: ["operational-metrics"], queryFn: getOperationalMetrics, ...queryRefreshOptions });
  const jobsQuery = useQuery({ queryKey: ["jobs", "dashboard"], queryFn: () => getJobs({ limit: 200 }), ...queryRefreshOptions });
  const queuesQuery = useQuery({ queryKey: ["queues"], queryFn: getQueues, ...queryRefreshOptions });
  const activityQuery = useQuery({
    queryKey: ["activity-feed", "dashboard"],
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

  const prioritizedActions = useMemo<ControlCenterAction[]>(() => {
    const pendingReview = statsQuery.data?.records.pending ?? 0;
    const failedJobs = jobsQuery.data?.items.filter((job) => job.status === "failed").length ?? 0;
    const pausedQueues = queuesQuery.data?.items.reduce((acc, q) => acc + q.paused, 0) ?? 0;

    const unhealthySources = sourcesQuery.data?.items.filter((source) =>
      source.status === "error" || source.operational_status === "degraded" || source.operational_status === "failed",
    ) ?? [];
    const staleSources = sourcesQuery.data?.items.filter((source) => {
      if (!source.last_crawled_at) return true;
      const ageMs = Date.now() - new Date(source.last_crawled_at).getTime();
      return ageMs > 7 * 24 * 60 * 60 * 1000;
    }) ?? [];

    const failedJobsConfidence = clamp((100 - failedJobs * 12) / 100);
    const pendingReviewConfidence = clamp((100 - pendingReview * 0.5) / 100);

    const draftActions: Array<Omit<ControlCenterAction, "priorityScore"> & { freshness: number }> = [
      {
        id: "drift-pending-review",
        type: "drift",
        title: "Resolve moderation backlog",
        description: "Pending records are delaying exports and increasing downstream data drift.",
        impactSummary:
          pendingReview > 0
            ? `${Math.min(100, Math.round((pendingReview / Math.max(statsQuery.data?.records.total ?? 1, 1)) * 100))}% of records are still pending moderation (${pendingReview} records).`
            : "No moderation backlog detected.",
        severity: severityForCount(pendingReview, { critical: 75, high: 30, medium: 10 }),
        confidence: pendingReviewConfidence,
        impactCount: pendingReview,
        cta: {
          label: "Review records",
          to: "/records?status=pending&sort=created_at:desc",
        },
        freshness: computeFreshness(jobsQuery.data?.items.find((job) => job.status === "failed")?.completed_at ?? null),
      },
      {
        id: "repair-failed-jobs",
        type: "repair",
        title: "Repair failed pipeline jobs",
        description: "Retry failed pipeline runs to prevent stale pages and extraction gaps.",
        impactSummary:
          failedJobs > 0
            ? `${failedJobs} pipeline jobs failed and may block new records from being extracted.`
            : "No failed jobs in the current dashboard window.",
        severity: severityForCount(failedJobs, { critical: 10, high: 5, medium: 1 }),
        confidence: failedJobsConfidence,
        impactCount: failedJobs,
        cta: {
          label: "Open failed jobs",
          to: "/jobs?status=failed&sort=completed_at:desc",
        },
        freshness: computeFreshness(jobsQuery.data?.items.find((job) => job.status === "failed")?.completed_at),
      },
      {
        id: "source-health",
        type: "source",
        title: "Address unhealthy sources",
        description: "Sources in degraded/error state can skew coverage and extraction quality.",
        impactSummary:
          unhealthySources.length > 0
            ? `${unhealthySources.length} sources report degraded health and need operator review.`
            : "All connected sources currently report healthy operational status.",
        severity: severityForCount(unhealthySources.length, { critical: 8, high: 4, medium: 1 }),
        impactCount: unhealthySources.length,
        sourceId: unhealthySources[0]?.id,
        cta: {
          label: "Inspect sources",
          to: unhealthySources[0]
            ? `/sources?status=error&source=${encodeURIComponent(unhealthySources[0].id)}`
            : "/sources?status=active",
        },
        freshness: computeFreshness(unhealthySources[0]?.last_crawled_at),
      },
      {
        id: "crawl-staleness",
        type: "crawl",
        title: "Refresh stale source crawls",
        description: "Older crawls reduce confidence that records reflect current source content.",
        impactSummary:
          staleSources.length > 0
            ? `${staleSources.length} sources have not been crawled in the last 7 days.`
            : "No stale sources detected in the configured freshness window.",
        severity: severityForCount(staleSources.length, { critical: 15, high: 8, medium: 3 }),
        confidence: clamp((100 - staleSources.length * 7) / 100),
        impactCount: staleSources.length,
        sourceId: staleSources[0]?.id,
        cta: {
          label: "Queue recrawl",
          to: staleSources[0]
            ? `/sources/${encodeURIComponent(staleSources[0].id)}/operations?filter=stale`
            : "/sources?status=active&sort=last_crawled_at:desc",
        },
        freshness: computeFreshness(staleSources[0]?.last_crawled_at),
      },
      {
        id: "queue-paused",
        type: "repair",
        title: "Resume paused queue workers",
        description: "Paused workers stop ingestion throughput and delay downstream classification.",
        impactSummary:
          pausedQueues > 0
            ? `${pausedQueues} queue workers are paused and currently not processing backlog.`
            : "All queue workers are active.",
        severity: severityForCount(pausedQueues, { critical: 6, high: 3, medium: 1 }),
        confidence: clamp((100 - pausedQueues * 15) / 100),
        impactCount: pausedQueues,
        cta: {
          label: "Open queues",
          to: "/queues?status=paused&sort=oldest_item_age_seconds:desc",
        },
        freshness: computeFreshness(new Date().toISOString()),
      },
    ];

    return draftActions
      .map((action) => ({
        ...action,
        priorityScore: computePriorityScore(action, action.freshness),
      }))
      .sort((a, b) => b.priorityScore - a.priorityScore);
  }, [jobsQuery.data, queuesQuery.data, sourcesQuery.data, statsQuery.data]);

  const prioritizedActionsError = statsQuery.isError || jobsQuery.isError || queuesQuery.isError || sourcesQuery.isError;

  return {
    statsQuery,
    sourcesQuery,
    metricsQuery,
    jobsQuery,
    queuesQuery,
    activityQuery,
    successRate,
    prioritizedActions,
    prioritizedActionsError,
    retryPrioritizedActions: () => {
      void statsQuery.refetch();
      void jobsQuery.refetch();
      void queuesQuery.refetch();
      void sourcesQuery.refetch();
    },
  };
}
