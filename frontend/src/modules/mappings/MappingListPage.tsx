import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { useMappings } from "@/api/mappings";
import { Button, EmptyState, Skeleton } from "@/components/ui";

export function MappingListPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch, error } = useMappings();

  const sortedMappings = useMemo(
    () => [...(data?.items ?? [])].sort((a, b) => (b.drift_impact ?? 0) - (a.drift_impact ?? 0)),
    [data?.items],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load mappings"
        description={error instanceof Error ? error.message : "Mapping list request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Mappings</h1>
        <Button variant="secondary" onClick={() => void refetch()}>
          <RefreshCcw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      <div className="rounded-lg border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Version</th>
              <th className="p-3 text-left">Status</th>
              <th className="p-3 text-left">Drift impact</th>
              <th className="p-3 text-left">Last updated</th>
            </tr>
          </thead>
          <tbody>
            {sortedMappings.map((mapping) => (
              <tr
                key={mapping.id}
                className="border-t cursor-pointer hover:bg-muted/30"
                onClick={() => navigate(`/mappings/${mapping.id}`)}
              >
                <td className="p-3 font-medium">{mapping.name}</td>
                <td className="p-3">v{mapping.version}</td>
                <td className={`p-3 font-medium ${mapping.status === "degraded" ? "text-red-600" : "text-emerald-600"}`}>
                  {mapping.status}
                </td>
                <td className={`p-3 ${mapping.drift_impact > 0.5 ? "text-red-600" : "text-amber-600"}`}>
                  {Math.round(mapping.drift_impact * 100)}%
                </td>
                <td className="p-3">{new Date(mapping.updated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
