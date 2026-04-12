import { useQuery } from "@tanstack/react-query";
import { getStats, getSources } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";

export function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const recentSources = sources?.items?.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Total Sources"
          value={stats?.sources.total ?? 0}
        />
        <StatCard
          label="Total Records"
          value={stats?.records.total ?? 0}
          sub={`${stats?.records.pending ?? 0} pending · ${stats?.records.approved ?? 0} approved`}
        />
        <StatCard
          label="Pages Crawled"
          value={stats?.pages.crawled ?? 0}
        />
        <StatCard
          label="Export Ready"
          value={stats?.records.approved ?? 0}
          highlight
        />
      </div>

      {/* Records by type */}
      <div className="grid grid-cols-2 gap-6">
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
      </div>

      {/* Recent sources */}
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
                  <div className="text-xs text-gray-500">{source.url}</div>
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
