import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRecords, approveRecord, rejectRecord, bulkApprove, getSources, type ArtRecord } from "@/lib/api";
import { RecordTableRow } from "@/components/records/RecordTableRow";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { Button, Input, Select } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";

const PAGE_SIZE = 25;

export function Records() {
  const isMobile = useIsMobile();
  const [sourceId, setSourceId] = useState("");
  const [recordType, setRecordType] = useState("");
  const [statusTab, setStatusTab] = useState<"pending" | "approved" | "rejected">("pending");
  const [confidenceBand, setConfidenceBand] = useState("");
  const [search, setSearch] = useState("");
  const [skip, setSkip] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const baseFilters = {
    source_id: sourceId || undefined,
    record_type: recordType || undefined,
    confidence_band: confidenceBand || undefined,
    search: search || undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["records", { ...baseFilters, status: statusTab, skip, limit: PAGE_SIZE }],
    queryFn: () =>
      getRecords({
        ...baseFilters,
        status: statusTab,
        skip,
        limit: PAGE_SIZE,
      }),
  });

  const pendingCount = useQuery({
    queryKey: ["record-count", { ...baseFilters, status: "pending" }],
    queryFn: () => getRecords({ ...baseFilters, status: "pending", limit: 1 }),
  });
  const approvedCount = useQuery({
    queryKey: ["record-count", { ...baseFilters, status: "approved" }],
    queryFn: () => getRecords({ ...baseFilters, status: "approved", limit: 1 }),
  });
  const rejectedCount = useQuery({
    queryKey: ["record-count", { ...baseFilters, status: "rejected" }],
    queryFn: () => getRecords({ ...baseFilters, status: "rejected", limit: 1 }),
  });

  const invalidateRecordQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["records"] });
    queryClient.invalidateQueries({ queryKey: ["record-count"] });
  };

  const approveMutation = useMutation({
    mutationFn: approveRecord,
    onSuccess: invalidateRecordQueries,
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectRecord(id),
    onSuccess: invalidateRecordQueries,
  });

  const bulkApproveMutation = useMutation({
    mutationFn: () => bulkApprove({ source_id: sourceId || "all", min_confidence: 70 }),
    onSuccess: invalidateRecordQueries,
  });

  const visibleIds = useMemo(() => data?.items.map((item) => item.id) ?? [], [data?.items]);
  const selectedCount = selectedIds.size;

  const toggleSelected = (id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const toggleAllVisible = (checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const id of visibleIds) {
        if (checked) next.add(id);
        else next.delete(id);
      }
      return next;
    });
  };

  const runBulkStatusUpdate = async (action: "approve" | "reject") => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (action === "approve") {
      await Promise.all(ids.map((id) => approveRecord(id)));
    } else {
      await Promise.all(ids.map((id) => rejectRecord(id)));
    }
    setSelectedIds(new Set());
    invalidateRecordQueries();
  };

  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Records</h1>
        <Button
          fullWidth={isMobile}
          className="sm:w-auto"
          onClick={() => {
            if (confirm("Approve all HIGH confidence records?")) bulkApproveMutation.mutate();
          }}
          variant="primary"
          loading={bulkApproveMutation.isPending}
        >
          Approve all HIGH
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <StatusTab label="Pending" count={pendingCount.data?.total ?? 0} active={statusTab === "pending"} onClick={() => { setStatusTab("pending"); setSkip(0); }} />
        <StatusTab label="Approved" count={approvedCount.data?.total ?? 0} active={statusTab === "approved"} onClick={() => { setStatusTab("approved"); setSkip(0); }} />
        <StatusTab label="Rejected" count={rejectedCount.data?.total ?? 0} active={statusTab === "rejected"} onClick={() => { setStatusTab("rejected"); setSkip(0); }} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Select
          value={sourceId}
          onChange={(e) => { setSourceId(e.target.value); setSkip(0); }}
          className="w-full"
          options={[{ value: "", label: "All sources" }, ...(sources?.items.map((s) => ({ value: s.id, label: s.name ?? s.url })) ?? [])]}
        />
        <Select
          value={recordType}
          onChange={(e) => { setRecordType(e.target.value); setSkip(0); }}
          className="w-full"
          options={[
            { value: "", label: "All types" },
            ...["artist", "event", "exhibition", "venue", "artwork"].map((t) => ({ value: t, label: t })),
          ]}
        />
        <Select
          value={confidenceBand}
          onChange={(e) => { setConfidenceBand(e.target.value); setSkip(0); }}
          className="w-full"
          options={[
            { value: "", label: "All confidence" },
            ...["HIGH", "MEDIUM", "LOW"].map((b) => ({ value: b, label: b })),
          ]}
        />
        <Input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setSkip(0); }}
          placeholder="Search title..."
          className="w-full"
        />
      </div>

      {selectedCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="text-sm text-blue-800">{selectedCount} selected</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full sm:w-auto">
            <Button size="sm" fullWidth={isMobile} onClick={() => runBulkStatusUpdate("approve")}>Approve selected ({selectedCount})</Button>
            <Button size="sm" fullWidth={isMobile} variant="danger" onClick={() => runBulkStatusUpdate("reject")}>Reject selected ({selectedCount})</Button>
            <Button size="sm" fullWidth={isMobile} variant="ghost" onClick={() => setSelectedIds(new Set())}>Clear selection</Button>
          </div>
        </div>
      )}

      {isMobile ? (
        <div className="space-y-3">
          {data?.items.map((record) => (
            <RecordMobileCard key={record.id} record={record} onToggleSelected={toggleSelected} onApprove={approveMutation.mutate} onReject={rejectMutation.mutate} selected={selectedIds.has(record.id)} />
          ))}
          {!isLoading && data?.items.length === 0 && (
            <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground/80">No records found.</div>
          )}
        </div>
      ) : (
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left p-3">
                <input
                  type="checkbox"
                  onChange={(e) => toggleAllVisible(e.target.checked)}
                  checked={visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))}
                />
              </th>
              <th className="text-left p-3 font-medium text-muted-foreground">Record</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Type</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Confidence</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Source</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="text-center p-8 text-muted-foreground/80">Loading...</td></tr>
            )}
            {data?.items.map((record) => (
              <RecordTableRow
                key={record.id}
                record={record}
                selected={selectedIds.has(record.id)}
                onToggleSelected={toggleSelected}
                onApprove={(id) => approveMutation.mutate(id)}
                onReject={(id) => rejectMutation.mutate(id)}
              />
            ))}
            {!isLoading && data?.items.length === 0 && (
              <tr><td colSpan={6} className="text-center p-8 text-muted-foreground/80">No records found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-2">
        <Button
          fullWidth={isMobile}
          onClick={() => setSkip((prev) => Math.max(0, prev - PAGE_SIZE))}
          disabled={skip === 0}
          variant="secondary"
        >
          Prev
        </Button>
        <Button
          fullWidth={isMobile}
          onClick={() => setSkip((prev) => prev + PAGE_SIZE)}
          disabled={(data?.items.length ?? 0) < PAGE_SIZE}
          variant="secondary"
        >
          Next
        </Button>
      </div>
    </div>
  );
}

function RecordMobileCard({
  record,
  selected,
  onToggleSelected,
  onApprove,
  onReject,
}: {
  record: ArtRecord;
  selected: boolean;
  onToggleSelected: (id: string, checked: boolean) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  return (
    <MobileCard>
      <div className="flex items-start gap-3">
        <input type="checkbox" checked={selected} onChange={(e) => onToggleSelected(record.id, e.target.checked)} aria-label={`select-${record.id}`} className="mt-1 h-4 w-4" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-sm text-foreground line-clamp-2">{record.title ?? "Untitled"}</h3>
            <RecordTypeBadge type={record.record_type} />
          </div>
          <MobileCardRow label="Confidence" value={<ConfidenceBadge band={record.confidence_band as "HIGH" | "MEDIUM" | "LOW"} score={record.confidence_score} />} />
          <MobileCardRow label="Source" value={<span className="max-w-[140px] truncate inline-block align-bottom">{record.source_id}</span>} />
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Button size="sm" onClick={() => onApprove(record.id)}>Approve</Button>
            <Button size="sm" variant="danger" onClick={() => onReject(record.id)}>Reject</Button>
          </div>
        </div>
      </div>
    </MobileCard>
  );
}

function StatusTab({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded text-sm border ${
        active
          ? "bg-blue-600 text-white border-blue-600"
          : "bg-card text-muted-foreground border-border hover:bg-muted/40"
      }`}
    >
      {label} ({count})
    </button>
  );
}
