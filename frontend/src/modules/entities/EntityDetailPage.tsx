import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, History } from "lucide-react";
import { useEntity, useEntityHistory, useUndoMerge, useUndoMergeSupport } from "@/api/entities";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { Button, EmptyState, Modal, ModalContent, ModalFooter, Skeleton } from "@/components/ui";
import { ConflictBadge, deriveConflictSeverity } from "@/modules/entities/components/ConflictBadge";
import { DecisionHistoryPanel } from "@/modules/entities/components/DecisionHistoryPanel";
import { RelationshipList } from "@/modules/entities/components/RelationshipList";
import { SourceVariantCard } from "@/modules/entities/components/SourceVariantCard";

const isDevMode = import.meta.env.DEV;

export function EntityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: entity, isLoading, isError, error, refetch } = useEntity(id);
  const {
    data: decisionHistory = [],
    isLoading: isHistoryLoading,
    isError: isHistoryError,
  } = useEntityHistory(id);
  const { data: undoSupport } = useUndoMergeSupport(id);
  const undoMergeMutation = useUndoMerge();

  const [isUndoModalOpen, setIsUndoModalOpen] = useState(false);

  const canonicalValues = useMemo(
    () => Object.fromEntries((entity?.canonical_fields ?? []).map((field) => [field.field, field.value])),
    [entity?.canonical_fields],
  );

  const conflictStatus = useMemo(() => {
    if (!entity || entity.conflicts.length === 0) return "none" as const;
    const severities = entity.conflicts.map((conflict) =>
      deriveConflictSeverity({
        sourceCount: conflict.options?.length,
        confidenceValues: (conflict.options ?? []).map((option) => option.confidence),
        values: (conflict.options ?? []).map((option) => option.value),
      }),
    );
    if (severities.includes("major")) return "major" as const;
    if (severities.includes("medium")) return "medium" as const;
    return "minor" as const;
  }, [entity]);

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

  async function handleUndoMerge() {
    if (!id) return;
    const actionPayload = { action: "undo-merge", entityId: id };
    if (isDevMode) {
      console.debug("EntityAction", actionPayload);
    }
    await undoMergeMutation.mutateAsync(id);
    setIsUndoModalOpen(false);
  }

  const undoImpact = undoSupport?.impact;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border bg-card p-4">
        <h1 className="text-2xl font-bold">{entity.name}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{entity.type}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-5">
          <div><p className="text-xs uppercase text-muted-foreground">Confidence</p><div className="mt-1"><ConfidenceBar score={entity.confidence_score} /></div></div>
          <div><p className="text-xs uppercase text-muted-foreground">Sources</p><p className="text-lg font-semibold">{entity.source_count}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">Conflicts</p><ConflictBadge status={conflictStatus} /></div>
          <div><p className="text-xs uppercase text-muted-foreground">Last merged</p><p className="text-sm">{entity.last_merged ? new Date(entity.last_merged).toLocaleString() : "Never"}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">Updated</p><p className="text-sm">{new Date(entity.last_updated).toLocaleString()}</p></div>
        </div>
        <div className="mt-4">
          <Button
            variant="warning"
            disabled={!undoSupport?.supported || undoMergeMutation.isPending}
            onClick={() => setIsUndoModalOpen(true)}
            title={undoSupport?.supported ? "Revert the latest merge decision" : "Undo not supported yet"}
          >
            Undo last merge
          </Button>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Canonical View</h2>
        <div className="mt-3 overflow-hidden rounded border">
          <table className="w-full text-sm">
            <thead className="bg-muted/40"><tr><th className="p-2 text-left">Field</th><th className="p-2 text-left">Value</th><th className="p-2 text-left">Confidence</th><th className="p-2 text-left">Provenance</th></tr></thead>
            <tbody>
              {entity.canonical_fields.length === 0 ? (
                <tr className="border-t">
                  <td className="p-2 text-muted-foreground" colSpan={4}>No canonical fields available yet.</td>
                </tr>
              ) : entity.canonical_fields.map((field) => {
                const sources = field.sources && field.sources.length > 0
                  ? field.sources
                  : field.source
                    ? [{ source: field.source, confidence: field.confidence }]
                    : [];

                return (
                  <tr key={field.field} className="border-t align-top">
                    <td className="p-2 font-medium">{field.field}</td>
                    <td className="p-2">{field.value || "—"}</td>
                    <td className="min-w-[220px] p-2"><ConfidenceBar score={field.confidence} /></td>
                    <td className="p-2">
                      {sources.length === 0 ? (
                        <span className="text-muted-foreground">No source attribution available</span>
                      ) : (
                        <ul className="space-y-1">
                          {sources.map((source) => (
                            <li key={`${field.field}-${source.source}`} className="text-xs">
                              {source.source}
                              {typeof source.confidence === "number" ? ` (${Math.round(source.confidence * 100)}%)` : ""}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                );
              })}
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
          <p className="text-sm text-muted-foreground">No conflicts detected — entity is consistent across sources.</p>
        ) : (
          <ul className="space-y-2">
            {entity.conflicts.map((conflict) => {
              const computedSeverity = deriveConflictSeverity({
                sourceCount: conflict.options?.length,
                confidenceValues: (conflict.options ?? []).map((option) => option.confidence),
                values: (conflict.options ?? []).map((option) => option.value),
              });

              return (
                <li key={conflict.field} className="rounded border p-3">
                  <div className="flex items-center justify-between"><p className="font-medium">{conflict.field}</p><ConflictBadge status={computedSeverity} /></div>
                  <p className="mt-1 text-sm text-muted-foreground">{conflict.explanation}</p>
                  <Link className="mt-2 inline-block text-sm text-primary underline" to={`/entities/${entity.id}/conflicts?field=${encodeURIComponent(conflict.field)}`}>Resolve conflict</Link>
                </li>
              );
            })}
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

      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Decision History</h2>
        </div>
        {isHistoryLoading ? <Skeleton className="h-32 rounded-lg" /> : null}
        {!isHistoryLoading && isHistoryError ? (
          <div className="rounded border bg-card p-4 text-sm text-muted-foreground">Unable to load decision history right now.</div>
        ) : null}
        {!isHistoryLoading && !isHistoryError ? <DecisionHistoryPanel items={decisionHistory} /> : null}
      </section>

      <Modal open={isUndoModalOpen} onClose={() => setIsUndoModalOpen(false)} title="Undo last merge">
        <ModalContent className="space-y-3">
          <p className="text-sm">This will split the merged entity back into original entities.</p>
          <p className="text-sm text-amber-700">
            This will restore {undoImpact?.restored_entities ?? 2} entities and re-link {undoImpact?.relinked_records ?? 0} records.
          </p>
          {undoMergeMutation.isError ? (
            <p className="text-sm text-red-700">{undoMergeMutation.error instanceof Error ? undoMergeMutation.error.message : "Undo merge failed."}</p>
          ) : null}
        </ModalContent>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsUndoModalOpen(false)}>Cancel</Button>
          <Button variant="warning" loading={undoMergeMutation.isPending} onClick={() => void handleUndoMerge()}>Confirm undo merge</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
