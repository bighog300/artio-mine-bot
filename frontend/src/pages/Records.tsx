import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getRecords, approveRecord, rejectRecord, bulkApprove, getSources } from "@/lib/api";
import { RecordTableRow } from "@/components/records/RecordTableRow";

const PAGE_SIZE = 25;

export function Records() {
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Records</h1>
        <button
          onClick={() => {
            if (confirm("Approve all HIGH confidence records?")) bulkApproveMutation.mutate();
          }}
          className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
        >
          Approve all HIGH
        </button>
      </div>

      <div className="flex gap-2">
        <StatusTab label="Pending" count={pendingCount.data?.total ?? 0} active={statusTab === "pending"} onClick={() => { setStatusTab("pending"); setSkip(0); }} />
        <StatusTab label="Approved" count={approvedCount.data?.total ?? 0} active={statusTab === "approved"} onClick={() => { setStatusTab("approved"); setSkip(0); }} />
        <StatusTab label="Rejected" count={rejectedCount.data?.total ?? 0} active={statusTab === "rejected"} onClick={() => { setStatusTab("rejected"); setSkip(0); }} />
      </div>

      <div className="flex gap-3 flex-wrap">
        <select
          value={sourceId}
          onChange={(e) => { setSourceId(e.target.value); setSkip(0); }}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All sources</option>
          {sources?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
          ))}
        </select>
        <select
          value={recordType}
          onChange={(e) => { setRecordType(e.target.value); setSkip(0); }}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All types</option>
          {[
            "artist",
            "event",
            "exhibition",
            "venue",
            "artwork",
          ].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={confidenceBand}
          onChange={(e) => { setConfidenceBand(e.target.value); setSkip(0); }}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All confidence</option>
          {["HIGH", "MEDIUM", "LOW"].map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setSkip(0); }}
          placeholder="Search title..."
          className="border border-gray-300 rounded px-2 py-1.5 text-sm flex-1 min-w-[200px]"
        />
      </div>

      {selectedCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 flex items-center justify-between">
          <div className="text-sm text-blue-800">{selectedCount} selected</div>
          <div className="flex items-center gap-2">
            <button onClick={() => runBulkStatusUpdate("approve")} className="px-2 py-1 text-xs bg-green-600 text-white rounded">Approve selected ({selectedCount})</button>
            <button onClick={() => runBulkStatusUpdate("reject")} className="px-2 py-1 text-xs border border-red-300 text-red-600 rounded">Reject selected ({selectedCount})</button>
            <button onClick={() => setSelectedIds(new Set())} className="px-2 py-1 text-xs text-gray-600 underline">Clear selection</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">
                <input
                  type="checkbox"
                  onChange={(e) => toggleAllVisible(e.target.checked)}
                  checked={visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id))}
                />
              </th>
              <th className="text-left p-3 font-medium text-gray-600">Record</th>
              <th className="text-left p-3 font-medium text-gray-600">Type</th>
              <th className="text-left p-3 font-medium text-gray-600">Confidence</th>
              <th className="text-left p-3 font-medium text-gray-600">Source</th>
              <th className="text-left p-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="text-center p-8 text-gray-400">Loading...</td></tr>
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
              <tr><td colSpan={6} className="text-center p-8 text-gray-400">No records found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          onClick={() => setSkip((prev) => Math.max(0, prev - PAGE_SIZE))}
          disabled={skip === 0}
          className="px-3 py-1.5 border border-gray-300 rounded text-sm disabled:opacity-50"
        >
          Prev
        </button>
        <button
          onClick={() => setSkip((prev) => prev + PAGE_SIZE)}
          disabled={(data?.items.length ?? 0) < PAGE_SIZE}
          className="px-3 py-1.5 border border-gray-300 rounded text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
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
          : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
      }`}
    >
      {label} ({count})
    </button>
  );
}
