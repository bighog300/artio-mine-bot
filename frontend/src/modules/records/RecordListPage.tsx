import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useRecords } from "@/api/records";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { Button, EmptyState, Select, Skeleton } from "@/components/ui";
import { getSources } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export function RecordListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mappingId = searchParams.get("mappingId") ?? searchParams.get("mapping_id") ?? undefined;
  const initialConfidence = searchParams.get("confidence") === "low" ? "LOW" : "";
  const [confidenceBand, setConfidenceBand] = useState(initialConfidence);
  const [sourceId, setSourceId] = useState("");
  const [recordType, setRecordType] = useState("");

  const { data, isLoading, isError, refetch, error } = useRecords({
    confidence_band: confidenceBand || undefined,
    source_id: sourceId || undefined,
    record_type: recordType || undefined,
    limit: 100,
  });
  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const sortedItems = useMemo(
    () => [...(data?.items ?? [])].sort((a, b) => a.confidence_score - b.confidence_score),
    [data?.items],
  );

  if (isLoading) return <Skeleton className="h-40 rounded-lg" />;
  if (isError) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Unable to load records"
        description={error instanceof Error ? error.message : "Records request failed."}
        actionLabel="Retry"
        onAction={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Records</h1>
        <Button variant="secondary" onClick={() => void refetch()}>Retry</Button>
      </div>
      {mappingId ? (
        <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Showing records from Mapping trace context: <span className="font-mono">{mappingId}</span>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <Select value={confidenceBand} onChange={(e) => setConfidenceBand(e.target.value)} options={[{ value: "", label: "All confidence" }, { value: "LOW", label: "Low" }, { value: "MEDIUM", label: "Medium" }, { value: "HIGH", label: "High" }]} />
        <Select
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          options={[{ value: "", label: "All sources" }, ...(sources?.items ?? []).map((source) => ({ value: source.id, label: source.name ?? source.url }))]}
        />
        <Select value={recordType} onChange={(e) => setRecordType(e.target.value)} options={[{ value: "", label: "All types" }, { value: "artist", label: "Artist" }, { value: "event", label: "Event" }, { value: "exhibition", label: "Exhibition" }, { value: "venue", label: "Venue" }, { value: "artwork", label: "Artwork" }]} />
      </div>

      {(data?.items?.length ?? 0) === 0 ? (<div className="rounded border bg-card p-6 text-sm text-muted-foreground">No records match this filter.</div>) : (<div className="rounded-lg border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-3 text-left">Record</th>
              <th className="p-3 text-left">Confidence</th>
              <th className="p-3 text-left">Source</th>
              <th className="p-3 text-left">Type</th>
              <th className="p-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((record) => (
              <tr key={record.id} className="border-t cursor-pointer hover:bg-muted/30" onClick={() => navigate(`/records/${record.id}`)}>
                <td className="p-3 font-medium">{record.title ?? "Untitled"}</td>
                <td className="p-3 min-w-[220px]"><ConfidenceBar score={record.confidence_score} /></td>
                <td className="p-3">{record.source_id}</td>
                <td className="p-3">{record.record_type}</td>
                <td className="p-3">{record.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>)}
    </div>
  );
}
