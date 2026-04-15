import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getActivityFeed, getJobs, getOperationalMetrics, getQueues, getStats, getSources } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatLogMessage, formatRelative } from "@/lib/utils";

export function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data: metrics } = useQuery({ queryKey: ["operational-metrics"], queryFn: getOperationalMetrics });
  const { data: activity, isError: isActivityError } = useQuery({
    queryKey: ["activity-feed"],
    queryFn: () => getActivityFeed({ limit: 20 }),
    refetchInterval: (query) => (query.state.status === "success" ? 10000 : false),
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
  const { data: jobs } = useQuery({ queryKey: ["jobs", "dashboard"], queryFn: () => getJobs({ limit: 200 }) });
  const { data: queues } = useQuery({ queryKey: ["queues"], queryFn: getQueues });

  const recentSources = sources?.items?.slice(0, 3) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Sources" value={stats?.sources.total ?? 0} />
        <StatCard
          label="Total Records"
          value={stats?.records.total ?? 0}
          sub={`${stats?.records.pending ?? 0} pending · ${stats?.records.approved ?? 0} approved`}
        />
        <StatCard label="Pages Crawled" value={stats?.pages.crawled ?? 0} />
        <StatCard label="Export Ready" value={stats?.records.approved ?? 0} highlight />
      </div>

      <div className="grid grid-cols-6 gap-3">
        <MiniMetric label="Artists" value={metrics?.total_artists ?? 0} />
        <MiniMetric label="Avg completeness" value={metrics?.avg_completeness ?? 0} />
        <MiniMetric label="Conflicts" value={metrics?.conflicts_count ?? 0} />
        <MiniMetric label="Duplicates" value={metrics?.duplicates_detected ?? 0} />
        <MiniMetric label="Merges" value={metrics?.merges_performed ?? 0} />
        <MiniMetric label="Pages processed" value={metrics?.pages_processed ?? 0} />
      </div>
      <div className="grid grid-cols-5 gap-3">
        <MiniMetric label="Jobs pending" value={jobs?.items.filter((j) => ["queued", "pending"].includes(j.status)).length ?? 0} />
        <MiniMetric label="Jobs running" value={jobs?.items.filter((j) => j.status === "running").length ?? 0} />
        <MiniMetric label="Jobs failed" value={jobs?.items.filter((j) => j.status === "failed").length ?? 0} />
        <MiniMetric label="Queues paused" value={queues?.items.reduce((acc, q) => acc + q.paused, 0) ?? 0} />
        <MiniMetric label="Oldest queue age (s)" value={queues?.items[0]?.oldest_item_age_seconds ?? 0} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-lg border p-4">
            <h2 className="font-semibold text-gray-900 mb-3">Records by Type</h2>
            <div className="space-y-2">
              {Object.entries(stats?.records.by_type ?? {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">{type}</span>
                  <span className="text-sm font-medium">{count as number}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg border p-4">
            <h2 className="font-semibold text-gray-900 mb-3">Confidence Distribution</h2>
            <div className="space-y-2">
              {Object.entries(stats?.records.by_confidence ?? {}).map(([band, count]) => (
                <div key={band} className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${band === "HIGH" ? "text-green-700" : band === "MEDIUM" ? "text-amber-700" : "text-red-700"}`}>
                    {band}
                  </span>
                  <span className="text-sm">{count as number}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg border">
            <div className="p-4 border-b">
              <h2 className="font-semibold text-gray-900">Recent Sources</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-3 text-gray-600 font-medium">Source</th>
                  <th className="text-left p-3 text-gray-600 font-medium">Status</th>
                  <th className="text-left p-3 text-gray-600 font-medium">Records</th>
                  <th className="text-left p-3 text-gray-600 font-medium">Last Run</th>
                </tr>
              </thead>
              <tbody>
                {recentSources.map((source) => (
                  <tr key={source.id} className="border-t hover:bg-gray-50">
                    <td className="p-3">
                      <div className="font-medium">{source.name ?? source.url}</div>
                      <div className="text-xs text-gray-500 truncate max-w-[240px]">{source.url}</div>
                    </td>
                    <td className="p-3"><StatusBadge status={source.status} /></td>
                    <td className="p-3">{source.total_records}</td>
                    <td className="p-3 text-gray-500">
                      {source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"}
                    </td>
                  </tr>
                ))}
                {recentSources.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-gray-400">
                      No sources yet. Add a source to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-3">Recent activity</h2>
          <div className="space-y-3">
            {activity?.items.map((item) => (
              <div key={item.id} className="flex items-start gap-2 text-sm">
                <span
                  className={`mt-1 h-2 w-2 rounded-full ${
                    item.level === "error"
                      ? "bg-red-500"
                      : item.level === "warning"
                        ? "bg-amber-500"
                        : "bg-green-500"
                  }`}
                />
                <div className="min-w-0">
                  <div className="text-gray-800 break-words">{formatLogMessage(item.message)}</div>
                  <div className="text-xs text-gray-500 flex items-center gap-2">
                    <span>{formatRelative(item.timestamp)}</span>
                    {item.source_id && (
                      <Link to={`/sources/${item.source_id}`} className="text-blue-600 hover:underline">
                        source
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {isActivityError && (
              <div className="text-sm text-amber-700">Activity feed is temporarily unavailable.</div>
            )}
            {!isActivityError && (!activity || activity.items.length === 0) && (
              <div className="text-sm text-gray-500">No activity yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border rounded p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function StatCard({ label, value, sub, highlight }: {
  label: string;
  value: number;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`bg-white rounded-lg border p-4 ${highlight ? "border-green-200" : ""}`}>
      <div className="text-sm text-gray-500 font-medium">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${highlight ? "text-green-600" : "text-gray-900"}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  );
}
