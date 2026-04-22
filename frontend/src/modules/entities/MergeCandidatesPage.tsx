import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useMergeCandidates } from "@/api/entities";
import { Button, EmptyState, Skeleton } from "@/components/ui";

export function MergeCandidatesPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useMergeCandidates();
  const [distinctIds, setDistinctIds] = useState<string[]>([]);

  const visibleCandidates = useMemo(
    () => (data ?? []).filter((candidate) => !distinctIds.includes(candidate.id)),
    [data, distinctIds],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load merge candidates"
        description={error instanceof Error ? error.message : "Merge candidate request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Merge Candidates</h1>
        <Button variant="secondary" onClick={() => void refetch()}>Refresh</Button>
      </div>

      {visibleCandidates.length === 0 ? (
        <div className="rounded border bg-card p-6 text-sm text-muted-foreground">No merge candidates detected — entities currently look distinct.</div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/40"><tr><th className="p-3 text-left">Pair</th><th className="p-3 text-left">Similarity</th><th className="p-3 text-left">Matching signals</th><th className="p-3 text-left">Actions</th></tr></thead>
            <tbody>
              {visibleCandidates.map((candidate) => (
                <tr key={candidate.id} className="border-t">
                  <td className="p-3">{candidate.entity_a.name} vs {candidate.entity_b.name}</td>
                  <td className="p-3">{Math.round(candidate.similarity_score * 100)}%</td>
                  <td className="p-3">
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground">Matched on:</p>
                      <ul className="list-inside list-disc space-y-0.5 text-xs">
                        <li>Name similarity: {Math.round((candidate.signal_breakdown?.name_similarity ?? candidate.similarity_score) * 100)}%</li>
                        <li>Shared relationships: {candidate.signal_breakdown?.shared_relationships ? "yes" : "no"}</li>
                        <li>Overlapping fields: {candidate.signal_breakdown?.overlapping_fields?.length ?? 0}</li>
                        <li>Conflicting fields: {(candidate.signal_breakdown?.conflicting_fields ?? []).join(", ") || "none"}</li>
                      </ul>
                      {candidate.matching_signals.length > 0 ? <p className="text-xs text-muted-foreground">Signals: {candidate.matching_signals.join(", ")}</p> : null}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      <Link className="text-sm text-primary underline" to={`/entities/compare/${candidate.entity_a.id}/${candidate.entity_b.id}?from=merge-candidates`}>Inspect</Link>
                      <Button size="sm" onClick={() => navigate(`/entities/compare/${candidate.entity_a.id}/${candidate.entity_b.id}?intent=merge&from=merge-candidates`)}>Merge</Button>
                      <Button size="sm" variant="outline" onClick={() => setDistinctIds((current) => [...current, candidate.id])}>Mark as distinct</Button>
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
