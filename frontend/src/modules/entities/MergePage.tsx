import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEntityComparison, useMergeEntities } from "@/api/entities";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { FieldComparisonTable } from "@/modules/entities/components/FieldComparisonTable";
import { MergePreviewPanel } from "@/modules/entities/components/MergePreviewPanel";

export function MergePage() {
  const { a, b } = useParams<{ a: string; b: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useEntityComparison(a, b);
  const mergeMutation = useMergeEntities();

  const rows = useMemo(() => {
    if (!data) return [];
    const keys = Array.from(new Set([...Object.keys(data.entity_a.fields ?? {}), ...Object.keys(data.entity_b.fields ?? {})]));
    return keys.map((field) => ({ field, valueA: data.entity_a.fields?.[field] ?? "", valueB: data.entity_b.fields?.[field] ?? "" }));
  }, [data]);

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load merge comparison"
        description={error instanceof Error ? error.message : "Merge comparison request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }
  if (!data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="No comparison available"
        description="Choose two entities from merge candidates to inspect differences."
        actionLabel="Open merge candidates"
        onAction={() => navigate("/entities/merge")}
      />
    );
  }

  async function executeMerge(primary: "a" | "b") {
    if (!data) return;
    const primaryId = primary === "a" ? data.entity_a.id : data.entity_b.id;
    const secondaryId = primary === "a" ? data.entity_b.id : data.entity_a.id;
    await mergeMutation.mutateAsync({ primary_entity_id: primaryId, secondary_entity_id: secondaryId });
    navigate(`/entities/${primaryId}`);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Merge Comparison</h1>
        <Link className="text-sm text-primary underline" to="/entities/merge">Back to candidates</Link>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Side-by-Side Comparison</h2>
        <FieldComparisonTable mode="merge" rows={rows} leftLabel={data.entity_a.name} rightLabel={data.entity_b.name} />
      </section>

      <MergePreviewPanel resultingFields={data.preview.resulting_fields} relationships={data.preview.combined_relationships} />

      <section className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Decision Panel</h2>
        <p className="mt-1 text-sm text-muted-foreground">Review differences and preview above. No silent data loss: merge actions are explicit.</p>
        {mergeMutation.isError ? <p className="mt-2 text-sm text-red-700">{mergeMutation.error instanceof Error ? mergeMutation.error.message : "Merge failed."}</p> : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button loading={mergeMutation.isPending} onClick={() => void executeMerge("a")}>Merge into {data.entity_a.name}</Button>
          <Button loading={mergeMutation.isPending} variant="secondary" onClick={() => void executeMerge("b")}>Merge into {data.entity_b.name}</Button>
          <Button variant="outline" onClick={() => navigate(-1)}>Cancel</Button>
        </div>
      </section>
    </div>
  );
}
