import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEntity } from "@/api/entities";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { EmptyState, Skeleton } from "@/components/ui";
import { ConflictBadge } from "@/modules/entities/components/ConflictBadge";
import { SourceVariantCard } from "@/modules/entities/components/SourceVariantCard";
import { RelationshipList } from "@/modules/entities/components/RelationshipList";

export function EntityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: entity, isLoading, isError, error, refetch } = useEntity(id);

  const canonicalValues = useMemo(
    () => Object.fromEntries((entity?.canonical_fields ?? []).map((field) => [field.field, field.value])),
    [entity?.canonical_fields],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load entity"
        description={error instanceof Error ? error.message : "Entity detail request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }
  if (!entity) return null;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border bg-card p-4">
        <h1 className="text-2xl font-bold">{entity.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{entity.type}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          <div><p className="text-xs uppercase text-muted-foreground">Confidence</p><div className="mt-1"><ConfidenceBar score={entity.confidence_score} /></div></div>
          <div><p className="text-xs uppercase text-muted-foreground">Sources</p><p className="text-lg font-semibold">{entity.source_count}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">Conflicts</p><ConflictBadge status={entity.conflicts.length ? entity.conflicts.some((c) => c.severity === "major") ? "major" : "minor" : "none"} /></div>
          <div><p className="text-xs uppercase text-muted-foreground">Last merged</p><p className="text-sm">{entity.last_merged ? new Date(entity.last_merged).toLocaleString() : "Never"}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">Updated</p><p className="text-sm">{new Date(entity.last_updated).toLocaleString()}</p></div>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Canonical View</h2>
        <div className="mt-3 overflow-hidden rounded border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40"><tr><th className="p-2 text-left">Field</th><th className="p-2 text-left">Value</th><th className="p-2 text-left">Confidence</th><th className="p-2 text-left">Source</th></tr></thead>
            <tbody>
              {entity.canonical_fields.map((field) => (
                <tr key={field.field} className="border-t"><td className="p-2 font-medium">{field.field}</td><td className="p-2">{field.value || "—"}</td><td className="min-w-[220px] p-2"><ConfidenceBar score={field.confidence} /></td><td className="p-2">{field.source}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Conflicts</h2>
          <Link className="text-sm text-primary underline" to={`/entities/${entity.id}/conflicts`}>Open resolution workspace</Link>
        </div>
        {entity.conflicts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No conflicts detected.</p>
        ) : (
          <ul className="space-y-2">
            {entity.conflicts.map((conflict) => (
              <li key={conflict.field} className="rounded border p-3">
                <div className="flex items-center justify-between"><p className="font-medium">{conflict.field}</p><ConflictBadge status={conflict.severity} /></div>
                <p className="mt-1 text-sm text-muted-foreground">{conflict.explanation}</p>
                <Link className="mt-2 inline-block text-sm text-primary underline" to={`/entities/${entity.id}/conflicts?field=${encodeURIComponent(conflict.field)}`}>Resolve conflict</Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Source Variants</h2>
        {entity.source_variants.length === 0 ? <div className="rounded border bg-card p-4 text-sm text-muted-foreground">No source variants available.</div> : entity.source_variants.map((variant) => <SourceVariantCard key={`${variant.source_name}-${variant.source_id ?? "unknown"}`} variant={variant} canonicalValues={canonicalValues} />)}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Relationships</h2>
        <RelationshipList items={entity.relationships} />
      </section>
    </div>
  );
}
