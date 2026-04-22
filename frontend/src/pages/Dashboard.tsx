import { Link, useNavigate } from "react-router-dom";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatLogMessage, formatRelative } from "@/lib/utils";
import { Button, EmptyState, Skeleton, SkeletonCardList, SkeletonStatCard, SkeletonTableRows } from "@/components/ui";
import { Activity, BarChart3, CircleDot, Database, Globe, PackageCheck, ScanSearch } from "lucide-react";
import { PrioritizedActionsPanel } from "@/features/control-center/components/PrioritizedActionsPanel";
import { useControlCenterData } from "@/features/control-center/useControlCenterData";

export function Dashboard() {
  const navigate = useNavigate();
  const {
    statsQuery,
    sourcesQuery,
    metricsQuery,
    jobsQuery,
    queuesQuery,
    activityQuery,
    successRate,
    prioritizedActions,
    prioritizedActionsError,
    retryPrioritizedActions,
  } = useControlCenterData();

  const { data: stats, isLoading: isStatsLoading } = statsQuery;
  const { data: sources, isLoading: isSourcesLoading } = sourcesQuery;
  const { data: metrics, isLoading: isMetricsLoading } = metricsQuery;
  const { data: jobs, isLoading: isJobsLoading } = jobsQuery;
  const { data: queues, isLoading: isQueuesLoading } = queuesQuery;
  const { data: activity, isError: isActivityError, isLoading: isActivityLoading } = activityQuery;

  const recentSources = sources?.items?.slice(0, 3) ?? [];

  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Dashboard</h1>
        <Button variant="secondary" onClick={() => navigate("/sources")}>Add Source</Button>
      </div>

      <PrioritizedActionsPanel
        isLoading={isStatsLoading || isJobsLoading || isQueuesLoading || isSourcesLoading}
        isError={prioritizedActionsError}
        onRetry={retryPrioritizedActions}
        actions={prioritizedActions}
      />

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3" role="status" aria-live="polite">
        <div className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">Drift summary</h2>
          <p className="mt-1 text-2xl font-bold text-foreground">{stats?.records.pending ?? 0}</p>
          <p className="text-xs text-muted-foreground">Records pending moderation and prone to downstream drift.</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">Source status</h2>
          <p className="mt-1 text-2xl font-bold text-foreground">{sources?.items.filter((s) => s.status !== "active").length ?? 0}</p>
          <p className="text-xs text-muted-foreground">Sources currently not in an active state.</p>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">Repair queue</h2>
          <p className="mt-1 text-2xl font-bold text-foreground">{jobs?.items.filter((j) => j.status === "failed").length ?? 0}</p>
          <p className="text-xs text-muted-foreground">Failed jobs waiting for retry or intervention.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-12" role="status" aria-live="polite">
        {isStatsLoading ? (
          <>
            <div className="lg:col-span-4"><SkeletonStatCard /></div>
            <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-3"><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /></div>
          </>
        ) : (
          <>
            <PrimaryStatCard label="Export Ready" value={stats?.records.approved ?? 0} sub="Approved records available for export" icon={PackageCheck} />
            <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <StatCard label="Total Sources" value={stats?.sources.total ?? 0} icon={Globe} />
              <StatCard label="Total Records" value={stats?.records.total ?? 0} sub={`${stats?.records.pending ?? 0} pending · ${stats?.records.approved ?? 0} approved`} icon={Database} />
              <StatCard label="Pages Crawled" value={stats?.pages.crawled ?? 0} icon={ScanSearch} />
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3" role="status" aria-live="polite">
        {(isMetricsLoading || isJobsLoading || isQueuesLoading) ? Array.from({ length: 7 }).map((_, idx) => <Skeleton key={idx} className="h-20 rounded border" />) : (
          <>
            <MiniMetric label="Artists" value={metrics?.total_artists ?? 0} tone="neutral" />
            <MiniMetric label="Avg completeness" value={metrics?.avg_completeness ?? 0} tone="info" />
            <MiniMetric label="Conflicts" value={metrics?.conflicts_count ?? 0} tone="warn" />
            <MiniMetric label="Duplicates" value={metrics?.duplicates_detected ?? 0} tone="warn" />
            <MiniMetric label="Merges" value={metrics?.merges_performed ?? 0} tone="success" />
            <MiniMetric label="Jobs failed" value={jobs?.items.filter((j) => j.status === "failed").length ?? 0} tone="danger" />
            <MiniMetric label="Success rate" value={successRate} suffix="%" tone="success" />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 lg:gap-6">
        <div className="space-y-6">
          <div className="bg-card rounded-lg border p-4">
            <h2 className="font-semibold text-foreground mb-3">Records by Type</h2>
            <div className="space-y-2" role="status" aria-live="polite">
              {isStatsLoading ? Array.from({ length: 5 }).map((_, idx) => <Skeleton key={idx} className="h-4 w-full" />) : (
                Object.entries(stats?.records.by_type ?? {}).length > 0 ? Object.entries(stats?.records.by_type ?? {}).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground capitalize">{type}</span>
                    <span className="text-sm font-medium">{count as number}</span>
                  </div>
                )) : (
                  <EmptyState icon={BarChart3} title="No record type data" description="Records by type will appear after your first extraction job completes." className="p-5" />
                )
              )}
            </div>
          </div>

          <div className="bg-card rounded-lg border p-4">
            <h2 className="font-semibold text-foreground mb-3">Confidence Distribution</h2>
            <div className="space-y-2" role="status" aria-live="polite">
              {isStatsLoading ? Array.from({ length: 3 }).map((_, idx) => <Skeleton key={idx} className="h-4 w-full" />) : Object.entries(stats?.records.by_confidence ?? {}).map(([band, count]) => (
                <div key={band} className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${band === "HIGH" ? "text-green-700 dark:text-green-400" : band === "MEDIUM" ? "text-amber-700 dark:text-amber-400" : "text-red-700 dark:text-red-400"}`}>{band}</span>
                  <span className="text-sm">{count as number}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-card rounded-lg border">
            <div className="p-4 border-b">
              <h2 className="font-semibold text-foreground">Recent Sources</h2>
            </div>
            <table className="w-full text-sm block overflow-x-auto lg:table">
              <thead className="bg-muted/40">
                <tr>
                  <th className="text-left p-3 text-muted-foreground font-medium">Source</th>
                  <th className="text-left p-3 text-muted-foreground font-medium">Status</th>
                  <th className="text-left p-3 text-muted-foreground font-medium">Records</th>
                  <th className="text-left p-3 text-muted-foreground font-medium">Last Run</th>
                </tr>
              </thead>
              <tbody>
                {isSourcesLoading && <SkeletonTableRows columns={4} rows={3} />}
                {recentSources.map((source) => (
                  <tr key={source.id} className="border-t hover:bg-muted/40">
                    <td className="p-3">
                      <div className="font-medium">{source.name ?? source.url}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-[240px]">{source.url}</div>
                    </td>
                    <td className="p-3"><StatusBadge status={source.status} /></td>
                    <td className="p-3">{source.total_records}</td>
                    <td className="p-3 text-muted-foreground">{source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"}</td>
                  </tr>
                ))}
                {!isSourcesLoading && recentSources.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-4">
                      <EmptyState icon={Globe} title="No sources added" description="Add a source to begin discovery and monitor recent source health from this dashboard." actionLabel="Add Source" onAction={() => navigate("/sources")} />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-card rounded-lg border p-4 lg:p-6">
          <h2 className="font-semibold text-foreground mb-3">Recent activity</h2>
          <div className="space-y-2 lg:space-y-3" role="status" aria-live="polite">
            {isActivityLoading && <SkeletonCardList rows={4} />}
            {activity?.items.map((item) => (
              <div key={item.id} className="flex items-start gap-2 text-sm p-2 rounded active:bg-muted/60">
                <span className={`mt-1 h-2 w-2 rounded-full ${item.level === "error" ? "bg-red-500" : item.level === "warning" ? "bg-amber-500" : "bg-green-500"}`} />
                <div className="min-w-0">
                  <div className="text-foreground break-words">{formatLogMessage(item.message)}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <span>{formatRelative(item.timestamp)}</span>
                    {item.source_id && <Link to={`/sources/${item.source_id}`} className="text-blue-600 hover:underline">source</Link>}
                  </div>
                </div>
              </div>
            ))}
            {isActivityError && <div className="text-sm text-amber-700" role="status">Activity feed is temporarily unavailable.</div>}
            {!isActivityLoading && !isActivityError && (!activity || activity.items.length === 0) && <EmptyState icon={Activity} title="No activity yet" description="Recent crawl and extraction updates will stream here once jobs are running." className="p-5" />}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <MiniMetric label="Jobs pending" value={jobs?.items.filter((j) => ["queued", "pending"].includes(j.status)).length ?? 0} tone="info" />
        <MiniMetric label="Jobs running" value={jobs?.items.filter((j) => j.status === "running").length ?? 0} tone="success" />
        <MiniMetric label="Queues paused" value={queues?.items.reduce((acc, q) => acc + q.paused, 0) ?? 0} tone="warn" />
        <MiniMetric label="Oldest queue age (s)" value={queues?.items[0]?.oldest_item_age_seconds ?? 0} tone="neutral" />
        <MiniMetric label="Pages processed" value={metrics?.pages_processed ?? 0} tone="neutral" />
      </div>
    </div>
  );
}

function PrimaryStatCard({ label, value, sub, icon: Icon }: { label: string; value: number; sub: string; icon: typeof PackageCheck }) {
  return (
    <div className="lg:col-span-4 rounded-xl border border-emerald-300 bg-emerald-50/60 p-5 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/30">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">{label}</p>
          <p className="mt-1 text-4xl font-bold text-emerald-700 dark:text-emerald-200">{value.toLocaleString()}</p>
          <p className="mt-1 text-xs text-emerald-700/80 dark:text-emerald-300/80">{sub}</p>
        </div>
        <div className="rounded-full bg-emerald-100 p-2 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300"><Icon className="h-5 w-5" /></div>
      </div>
    </div>
  );
}

function MiniMetric({ label, value, suffix, tone = "neutral" }: { label: string; value: number; suffix?: string; tone?: "neutral" | "success" | "warn" | "danger" | "info" }) {
  const toneStyles = {
    neutral: "text-foreground",
    success: "text-emerald-600 dark:text-emerald-400",
    warn: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
    info: "text-blue-600 dark:text-blue-400",
  } as const;

  return (
    <div className="bg-card border rounded p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-lg lg:text-xl font-semibold ${toneStyles[tone]}`}>{value}{suffix ?? ""}</div>
    </div>
  );
}

function StatCard({ label, value, sub, icon: Icon }: { label: string; value: number; sub?: string; icon: typeof CircleDot }) {
  return (
    <div className="bg-card rounded-lg border p-4 lg:p-5">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm text-muted-foreground font-medium">{label}</div>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="text-3xl lg:text-4xl font-bold mt-1 text-foreground">{value.toLocaleString()}</div>
      {sub && <div className="text-xs text-muted-foreground/80 mt-1">{sub}</div>}
    </div>
  );
}
