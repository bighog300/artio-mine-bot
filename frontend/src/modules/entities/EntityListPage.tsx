import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEntities } from "@/api/entities";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { Button, EmptyState, Select, Skeleton } from "@/components/ui";
import { ConflictBadge } from "@/modules/entities/components/ConflictBadge";

const conflictPriority = { major: 3, minor: 2, none: 1 } as const;

export function EntityListPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [conflictFilter, setConflictFilter] = useState("");

  const { data, isLoading, isError, error, refetch } = useEntities({ type: typeFilter || undefined, conflict_status: conflictFilter || undefined });

  const sorted = useMemo(
    () =>
      [...(data ?? [])].sort((a, b) => {
        const byConflict = conflictPriority[b.conflict_status] - conflictPriority[a.conflict_status];
        if (byConflict !== 0) return byConflict;
        return a.confidence_score - b.confidence_score;
      }),
    [data],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;

  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load entity queue"
        description={error instanceof Error ? error.message : "Entity request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Entity Queue</h1>
          <p className="text-sm text-muted-foreground">Prioritized by conflict severity first, then low confidence.</p>
        </div>
        <Button variant="secondary" onClick={() => void refetch()}>Refresh</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          options={[
            { value: "", label: "All entity types" },
            { value: "artist", label: "Artist" },
            { value: "exhibition", label: "Exhibition" },
            { value: "event", label: "Event" },
            { value: "venue", label: "Venue" },
            { value: "artwork", label: "Artwork" },
          ]}
        />
        <Select
          value={conflictFilter}
          onChange={(e) => setConflictFilter(e.target.value)}
          options={[
            { value: "", label: "All conflict states" },
            { value: "major", label: "Major" },
            { value: "minor", label: "Minor" },
            { value: "none", label: "None" },
          ]}
        />
      </div>

      {sorted.length === 0 ? (
        <div className="rounded border bg-card p-6 text-sm text-muted-foreground">No entities match the selected filters.</div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="p-3 text-left">Name</th>
                <th className="p-3 text-left">Type</th>
                <th className="p-3 text-left">Sources</th>
                <th className="p-3 text-left">Conflict</th>
                <th className="p-3 text-left">Confidence</th>
                <th className="p-3 text-left">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((entity) => (
                <tr key={entity.id} className="border-t hover:bg-muted/30">
                  <td className="p-3 font-medium"><Link className="text-primary underline" to={`/entities/${entity.id}`}>{entity.name}</Link></td>
                  <td className="p-3 capitalize">{entity.type}</td>
                  <td className="p-3">{entity.source_count}</td>
                  <td className="p-3"><ConflictBadge status={entity.conflict_status} /></td>
                  <td className="min-w-[220px] p-3"><ConfidenceBar score={entity.confidence_score} /></td>
                  <td className="p-3">{new Date(entity.last_updated).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
