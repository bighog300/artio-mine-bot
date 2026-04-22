import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useMapping, useTestMapping, useUpdateMapping } from "@/api/mappings";
import { Alert, Button, EmptyState, Skeleton } from "@/components/ui";
import { ExtractionPreview } from "@/modules/mappings/ExtractionPreview";
import { FieldHealthTable } from "@/modules/mappings/FieldHealthTable";
import { SelectorEditor } from "@/modules/mappings/SelectorEditor";

export function MappingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const fieldFromQuery = searchParams.get("field");
  const { data, isLoading, isError, refetch, error } = useMapping(id);
  const testMutation = useTestMapping();
  const updateMutation = useUpdateMapping();

  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [selectorDraft, setSelectorDraft] = useState("");

  const activeField = useMemo(
    () => data?.fields.find((field) => field.field_name === selectedField) ?? data?.fields[0],
    [data?.fields, selectedField],
  );

  useEffect(() => {
    if (!data?.fields.length) return;
    const initial = fieldFromQuery && data.fields.some((field) => field.field_name === fieldFromQuery)
      ? fieldFromQuery
      : data.fields[0].field_name;
    setSelectedField(initial);
  }, [data?.fields, fieldFromQuery]);

  useEffect(() => {
    if (activeField) setSelectorDraft(activeField.selector);
  }, [activeField?.field_name]);

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

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card p-4">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <p className="text-sm text-muted-foreground">Version v{data.version} · Updated {new Date(data.updated_at).toLocaleString()}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span className={data.status === "degraded" ? "text-red-600" : "text-emerald-600"}>Status: {data.status}</span>
          <span>Drift impact: {Math.round(data.drift_impact * 100)}%</span>
          <Link className="text-primary underline" to={`/records?mapping_id=${data.id}&sort=confidence:asc`}>
            View affected records
          </Link>
        </div>
      </div>

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
          testing={testMutation.isPending}
          saving={updateMutation.isPending}
          onChange={setSelectorDraft}
          onTest={() =>
            testMutation.mutate({ id: data.id, field_name: activeField.field_name, selector: selectorDraft })
          }
          onSave={() =>
            updateMutation.mutate({ id: data.id, field_name: activeField.field_name, selector: selectorDraft })
          }
        />
      ) : null}

      <ExtractionPreview result={testMutation.data ?? null} />

      {(testMutation.isError || updateMutation.isError) ? (
        <Alert
          variant="error"
          title="Mapping action failed"
          description={testMutation.error instanceof Error ? testMutation.error.message : updateMutation.error instanceof Error ? updateMutation.error.message : "Unknown mapping action failure."}
        />
      ) : null}

      <Button variant="secondary" onClick={() => void refetch()}>Retry mapping load</Button>
    </div>
  );
}
