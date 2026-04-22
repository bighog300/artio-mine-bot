import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useRecord } from "@/api/records";
import { ProvenanceTrail } from "@/components/data/ProvenanceTrail";
import { Alert, Button, EmptyState, Skeleton } from "@/components/ui";
import { FieldConfidenceTable, type FieldConfidenceRow } from "@/modules/records/FieldConfidenceTable";

export function RecordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: record, isLoading, isError, refetch, error } = useRecord(id);
  const [showRaw, setShowRaw] = useState(false);

  const fieldRows = useMemo<FieldConfidenceRow[]>(() => {
    if (!record) return [];
    const entries = Object.entries(record)
      .filter(([key, value]) => typeof value === "string" || value === null)
      .slice(0, 12);

    return entries.map(([field, value]) => ({
      field,
      value: typeof value === "string" ? value : "",
      confidence: Number(record.confidence_score) / 100,
    }));
  }, [record]);

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load record"
        description={error instanceof Error ? error.message : "Record detail request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }
  if (!record) return null;

  const mappingId = (record as { mapping_id?: string | null }).mapping_id;
  const pageId = (record as { page_id?: string | null }).page_id;
  const jobId = (record as { job_id?: string | null }).job_id;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-bold">{record.title ?? "Untitled record"}</h1>
          <div className="flex gap-2">
            {mappingId ? <Link className="text-sm text-primary underline" to={`/mappings/${mappingId}`}>View Mapping</Link> : null}
            <Link className="text-sm text-primary underline" to={`/sources/${record.source_id}`}>View Source</Link>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{record.record_type} · {record.status}</p>
      </div>

      {record.confidence_score < 60 ? (
        <Alert variant="warning" title="Low confidence record" description="Review weak or missing fields before approving downstream mapping changes." />
      ) : null}

      <div className="rounded-lg border bg-card p-4">
        <h2 className="text-lg font-semibold">Structured Data</h2>
        <dl className="mt-3 grid gap-3 md:grid-cols-2">
          {fieldRows.slice(0, 8).map((row) => (
            <div key={row.field} className="rounded border p-3">
              <dt className="text-xs uppercase text-muted-foreground">{row.field}</dt>
              <dd className="text-sm">{row.value || "—"}</dd>
            </div>
          ))}
        </dl>
      </div>

      <FieldConfidenceTable rows={fieldRows} />

      <ProvenanceTrail
        nodes={[
          { id: `source-${record.source_id}`, label: "Source", to: `/sources/${record.source_id}` },
          { id: `page-${pageId ?? "unknown"}`, label: "Page", to: pageId ? `/pages?page_id=${pageId}` : "/pages" },
          { id: `job-${jobId ?? "unknown"}`, label: "Job", to: jobId ? `/jobs/${jobId}` : "/jobs" },
          { id: `record-${record.id}`, label: "Record", to: `/records/${record.id}` },
        ]}
      />

      <div className="rounded-lg border bg-card p-4">
        <button className="text-sm text-primary underline" onClick={() => setShowRaw((prev) => !prev)}>
          {showRaw ? "Hide raw data" : "Show raw data"}
        </button>
        {showRaw ? <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(record, null, 2)}</pre> : null}
      </div>

      <Button variant="secondary" onClick={() => void refetch()}>Retry record load</Button>
    </div>
  );
}
