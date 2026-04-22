import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEntityConflicts, useResolveConflict } from "@/api/entities";
import { Button, EmptyState, Input, Select, Skeleton } from "@/components/ui";
import { FieldComparisonTable } from "@/modules/entities/components/FieldComparisonTable";

export function ConflictResolutionPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const queryField = searchParams.get("field") ?? "";

  const { data, isLoading, isError, error, refetch } = useEntityConflicts(id);
  const resolveMutation = useResolveConflict();

  const [selectedField, setSelectedField] = useState("");
  const [decision, setDecision] = useState<"keep_canonical" | "source" | "manual">("keep_canonical");
  const [sourceChoice, setSourceChoice] = useState("");
  const [manualValue, setManualValue] = useState("");

  useEffect(() => {
    const first = data?.conflicts?.[0]?.field ?? "";
    setSelectedField(queryField || first);
  }, [data?.conflicts, queryField]);

  const selectedConflict = useMemo(
    () => data?.conflicts.find((conflict) => conflict.field === selectedField),
    [data?.conflicts, selectedField],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load conflicts"
        description={error instanceof Error ? error.message : "Conflict request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }
  if (!data || data.conflicts.length === 0) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="No conflicts to resolve"
        description="This entity currently has no outstanding conflicts."
        actionLabel="Refresh"
        onAction={() => void refetch()}
      />
    );
  }

  const options = selectedConflict?.options ?? [];
  const impactCount = selectedConflict?.impact_count ?? 0;

  async function handleResolve() {
    if (!id || !selectedConflict) return;
    const payload = {
      entityId: id,
      field: selectedConflict.field,
      resolution_type: decision,
      value: decision === "manual" ? manualValue : decision === "source" ? options.find((opt) => opt.source === sourceChoice)?.value : selectedConflict.canonical_value,
      source: decision === "source" ? sourceChoice : undefined,
    } as const;

    await resolveMutation.mutateAsync(payload);
    await refetch();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Conflict Resolution</h1>

      <section className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Field Selector</h2>
        <div className="mt-2 max-w-md">
          <Select value={selectedField} onChange={(e) => setSelectedField(e.target.value)} options={data.conflicts.map((conflict) => ({ value: conflict.field, label: `${conflict.field} (${conflict.severity})` }))} />
        </div>
        {selectedConflict ? <p className="mt-2 text-sm text-muted-foreground">{selectedConflict.explanation}</p> : null}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Comparison Table</h2>
        <FieldComparisonTable mode="conflict" rows={options.map((option) => ({ source: option.source, value: option.value, confidence: option.confidence }))} />
      </section>

      <section className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Decision Panel</h2>
        <p className="mt-1 text-sm text-amber-700">This will update {impactCount} related records.</p>

        <div className="mt-3 space-y-3">
          <label className="flex items-center gap-2 text-sm"><input type="radio" name="decision" checked={decision === "keep_canonical"} onChange={() => setDecision("keep_canonical")} /> Keep current canonical value</label>
          <label className="flex items-center gap-2 text-sm"><input type="radio" name="decision" checked={decision === "source"} onChange={() => setDecision("source")} /> Choose value from source</label>
          {decision === "source" ? (
            <Select value={sourceChoice} onChange={(e) => setSourceChoice(e.target.value)} options={options.map((option) => ({ value: option.source, label: `${option.source} (${option.confidence})` }))} />
          ) : null}
          <label className="flex items-center gap-2 text-sm"><input type="radio" name="decision" checked={decision === "manual"} onChange={() => setDecision("manual")} /> Enter manual value</label>
          {decision === "manual" ? <Input value={manualValue} onChange={(e) => setManualValue(e.target.value)} placeholder="Manual canonical value" /> : null}
        </div>

        {resolveMutation.isError ? <p className="mt-2 text-sm text-red-700">{resolveMutation.error instanceof Error ? resolveMutation.error.message : "Resolution failed."}</p> : null}
        {resolveMutation.isSuccess ? <p className="mt-2 text-sm text-emerald-700">Conflict resolved successfully.</p> : null}

        <div className="mt-4">
          <Button loading={resolveMutation.isPending} onClick={() => void handleResolve()}>Resolve conflict</Button>
        </div>
      </section>
    </div>
  );
}
