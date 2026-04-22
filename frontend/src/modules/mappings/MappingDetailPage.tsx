import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useMapping, useTestMapping, useUpdateMapping } from "@/api/mappings";
import type { MappingTestResponse } from "@/lib/api";
import { RootCausePanel } from "@/components/data/RootCausePanel";
import { Alert, Button, EmptyState, Skeleton } from "@/components/ui";
import { ExtractionPreview } from "@/modules/mappings/ExtractionPreview";
import { FieldHealthTable } from "@/modules/mappings/FieldHealthTable";
import { SelectorEditor } from "@/modules/mappings/SelectorEditor";

function estimateSuccessRate(output: Array<{ value: string | null }>) {
  if (!output.length) return 0;
  const successCount = output.filter((item) => (item.value ?? "").trim().length > 0).length;
  return successCount / output.length;
}

export function MappingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const fieldFromQuery = searchParams.get("field");
  const { data, isLoading, isError, refetch, error } = useMapping(id);
  const testMutation = useTestMapping();
  const baselineTestMutation = useTestMapping();
  const updateMutation = useUpdateMapping();

  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [selectorDraft, setSelectorDraft] = useState("");
  const [baselinePreview, setBaselinePreview] = useState<MappingTestResponse | null>(null);
  const [latestPreview, setLatestPreview] = useState<MappingTestResponse | null>(null);
  const [testedSelector, setTestedSelector] = useState<string | null>(null);

  const activeField = useMemo(
    () => data?.fields.find((field) => field.field_name === selectedField) ?? data?.fields[0],
    [data?.fields, selectedField],
  );

  const rootCauseItems = useMemo(() => {
    if (!activeField) return [];
    const driftDetected = activeField.drift_indicator !== "stable";
    const confidenceDrop = Math.max(0, 0.9 - activeField.confidence_avg);
    const selectorFailurePct = Math.round((1 - activeField.success_rate) * 100);

    return [
      selectorFailurePct > 0 ? `Selector '${activeField.selector}' is failing on ${selectorFailurePct}% of pages.` : "",
      driftDetected ? "Drift was detected recently for this field family." : "",
      confidenceDrop > 0.1 ? `Confidence dropped by ${Math.round(confidenceDrop * 100)}% from expected baseline.` : "",
    ].filter(Boolean);
  }, [activeField]);

  const affectedRecordCount = useMemo(() => {
    const fieldFailures = data?.fields.reduce((acc, field) => acc + Math.round((1 - field.success_rate) * 100), 0) ?? 0;
    return Math.max(fieldFailures * 3, 0);
  }, [data?.fields]);

  const affectedSources = useMemo(() => {
    if (data?.source_id) return 1;
    return data?.fields.some((field) => field.drift_indicator !== "stable") ? 3 : 1;
  }, [data?.fields, data?.source_id]);

  useEffect(() => {
    if (!data?.fields.length) return;
    const initial = fieldFromQuery && data.fields.some((field) => field.field_name === fieldFromQuery)
      ? fieldFromQuery
      : data.fields[0].field_name;
    setSelectedField(initial);
  }, [data?.fields, fieldFromQuery]);

  useEffect(() => {
    if (!activeField || !id) return;
    setSelectorDraft(activeField.selector);
    setTestedSelector(null);
    setLatestPreview(null);
    baselineTestMutation.mutate(
      { id, field_name: activeField.field_name, selector: activeField.selector },
      { onSuccess: (response) => setBaselinePreview(response) },
    );
  }, [activeField?.field_name, id]);

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load mapping"
        description={error instanceof Error ? error.message : "Mapping detail request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }
  if (!data) return null;

  const confidenceByField = Object.fromEntries(data.fields.map((field) => [field.field_name, field.confidence_avg]));
  const previewResult = latestPreview ?? testMutation.data ?? null;
  const canSave = testedSelector === selectorDraft && !testMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card p-4">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <p className="text-sm text-muted-foreground">Version v{data.version} · Updated {new Date(data.updated_at).toLocaleString()}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span className={data.status === "degraded" ? "text-red-600" : "text-emerald-600"}>Status: {data.status}</span>
          <span>Drift impact: {Math.round(data.drift_impact * 100)}%</span>
          <Link className="text-primary underline" to={`/records?mappingId=${data.id}&mapping_id=${data.id}&field=${encodeURIComponent(activeField?.field_name ?? "")}&confidence=low`}>
            View affected records
          </Link>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">Affects {affectedRecordCount.toLocaleString()} records across {affectedSources} source{affectedSources === 1 ? "" : "s"}.</p>
      </div>

      <RootCausePanel
        items={rootCauseItems}
        mappingLink={`/records?mappingId=${data.id}&mapping_id=${data.id}&field=${encodeURIComponent(activeField?.field_name ?? "")}&confidence=low`}
        ctaLabel="View failing records"
        severity={activeField?.drift_indicator === "critical" ? "critical" : "high"}
      />

      {activeField && activeField.drift_indicator !== "stable" ? (
        <Alert
          variant="warning"
          title="Field health degraded"
          description="This field is drifting. Test a safer selector and save once structured preview looks correct."
        />
      ) : null}

      <FieldHealthTable
        fields={data.fields}
        selectedField={selectedField}
        onSelectField={setSelectedField}
      />

      {activeField ? (
        <SelectorEditor
          fieldName={activeField.field_name}
          selector={selectorDraft}
          testing={testMutation.isPending || baselineTestMutation.isPending}
          saving={updateMutation.isPending}
          canSave={canSave}
          baselineRate={activeField.success_rate}
          testRate={previewResult ? estimateSuccessRate(previewResult.output) : undefined}
          baselinePreview={baselinePreview}
          latestPreview={previewResult}
          onChange={setSelectorDraft}
          onTest={() =>
            testMutation.mutate(
              { id: data.id, field_name: activeField.field_name, selector: selectorDraft },
              {
                onSuccess: (response) => {
                  setLatestPreview(response);
                  setTestedSelector(selectorDraft);
                },
              },
            )
          }
          onSave={() =>
            updateMutation.mutate({ id: data.id, field_name: activeField.field_name, selector: selectorDraft })
          }
        />
      ) : null}

      <ExtractionPreview result={previewResult} confidenceByField={confidenceByField} />

      {(testMutation.isError || baselineTestMutation.isError || updateMutation.isError) ? (
        <Alert
          variant="error"
          title="Mapping action failed"
          description={testMutation.error instanceof Error ? testMutation.error.message : updateMutation.error instanceof Error ? updateMutation.error.message : baselineTestMutation.error instanceof Error ? baselineTestMutation.error.message : "Unknown mapping action failure."}
        />
      ) : null}

      <Button variant="secondary" onClick={() => void refetch()}>Retry mapping load</Button>
    </div>
  );
}
