import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEntityComparison, useMergeEntities, useUndoMerge, useUndoMergeSupport } from "@/api/entities";
import { Button, EmptyState, Modal, ModalContent, ModalFooter, Skeleton } from "@/components/ui";
import { FieldComparisonTable } from "@/modules/entities/components/FieldComparisonTable";
import { MergePreviewPanel } from "@/modules/entities/components/MergePreviewPanel";

const isDevMode = import.meta.env.DEV;

export function MergePage() {
  const { a, b } = useParams<{ a: string; b: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useEntityComparison(a, b);
  const mergeMutation = useMergeEntities();
  const undoMergeMutation = useUndoMerge();
  const { data: supportA } = useUndoMergeSupport(a);
  const { data: supportB } = useUndoMergeSupport(b);

  const [pendingPrimary, setPendingPrimary] = useState<"a" | "b" | null>(null);
  const [pendingUndoId, setPendingUndoId] = useState<string | null>(null);

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

  const impactCount = data.preview.combined_relationships.reduce((sum, relationship) => sum + relationship.count, 0);

  async function executeMerge() {
    if (!data || !pendingPrimary) return;
    const primaryId = pendingPrimary === "a" ? data.entity_a.id : data.entity_b.id;
    const secondaryId = pendingPrimary === "a" ? data.entity_b.id : data.entity_a.id;

    const actionPayload = { action: "merge-entities", primaryId, secondaryId };
    if (isDevMode) {
      console.debug("EntityAction", actionPayload);
    }

    await mergeMutation.mutateAsync({ primary_entity_id: primaryId, secondary_entity_id: secondaryId });
    setPendingPrimary(null);
    navigate(`/entities/${primaryId}`);
  }

  async function handleUndoMerge() {
    if (!pendingUndoId) return;
    const actionPayload = { action: "undo-merge", entityId: pendingUndoId };
    if (isDevMode) {
      console.debug("EntityAction", actionPayload);
    }

    await undoMergeMutation.mutateAsync(pendingUndoId);
    setPendingUndoId(null);
    await refetch();
  }

  const selectedUndoSupport = pendingUndoId === data.entity_a.id ? supportA : supportB;

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
        <p className="mt-1 text-sm text-amber-700">This will update {impactCount} records.</p>
        {mergeMutation.isError ? <p className="mt-2 text-sm text-red-700">{mergeMutation.error instanceof Error ? mergeMutation.error.message : "Merge failed."}</p> : null}
        <div className="mt-4 flex flex-wrap gap-2">
          <Button loading={mergeMutation.isPending} onClick={() => setPendingPrimary("a")}>Merge into {data.entity_a.name}</Button>
          <Button loading={mergeMutation.isPending} variant="secondary" onClick={() => setPendingPrimary("b")}>Merge into {data.entity_b.name}</Button>
          <Button
            variant="warning"
            disabled={!supportA?.supported || undoMergeMutation.isPending}
            title={supportA?.supported ? "Revert merge for this entity" : "Undo not supported yet"}
            onClick={() => setPendingUndoId(data.entity_a.id)}
          >
            Undo last merge ({data.entity_a.name})
          </Button>
          <Button
            variant="warning"
            disabled={!supportB?.supported || undoMergeMutation.isPending}
            title={supportB?.supported ? "Revert merge for this entity" : "Undo not supported yet"}
            onClick={() => setPendingUndoId(data.entity_b.id)}
          >
            Undo last merge ({data.entity_b.name})
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>Cancel</Button>
        </div>
      </section>

      <Modal open={pendingPrimary !== null} onClose={() => setPendingPrimary(null)} title="Confirm merge">
        <ModalContent className="space-y-2">
          <p className="text-sm">This will merge both entities into a single canonical record.</p>
          <p className="text-sm text-amber-700">This will update {impactCount} records.</p>
        </ModalContent>
        <ModalFooter>
          <Button variant="outline" onClick={() => setPendingPrimary(null)}>Cancel</Button>
          <Button loading={mergeMutation.isPending} onClick={() => void executeMerge()}>Confirm merge</Button>
        </ModalFooter>
      </Modal>

      <Modal open={pendingUndoId !== null} onClose={() => setPendingUndoId(null)} title="Undo last merge">
        <ModalContent className="space-y-2">
          <p className="text-sm">This will split the merged entity back into original entities.</p>
          <p className="text-sm text-amber-700">
            This will restore {selectedUndoSupport?.impact?.restored_entities ?? 2} entities and re-link {selectedUndoSupport?.impact?.relinked_records ?? 8} records.
          </p>
          {undoMergeMutation.isError ? <p className="text-sm text-red-700">{undoMergeMutation.error instanceof Error ? undoMergeMutation.error.message : "Undo merge failed."}</p> : null}
        </ModalContent>
        <ModalFooter>
          <Button variant="outline" onClick={() => setPendingUndoId(null)}>Cancel</Button>
          <Button variant="warning" loading={undoMergeMutation.isPending} onClick={() => void handleUndoMerge()}>Confirm undo merge</Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
