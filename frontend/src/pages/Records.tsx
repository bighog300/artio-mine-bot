import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getRecords, approveRecord, rejectRecord, bulkApprove, getSources, type ArtRecord } from "@/lib/api";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ImageThumbnail } from "@/components/shared/ImageThumbnail";
import { truncate } from "@/lib/utils";

export function Records() {
  const [sourceId, setSourceId] = useState("");
  const [recordType, setRecordType] = useState("");
  const [status, setStatus] = useState("");
  const [confidenceBand, setConfidenceBand] = useState("");
  const [search, setSearch] = useState("");

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data, isLoading } = useQuery({
    queryKey: ["records", { sourceId, recordType, status, confidenceBand, search }],
    queryFn: () =>
      getRecords({
        source_id: sourceId || undefined,
        record_type: recordType || undefined,
        status: status || undefined,
        confidence_band: confidenceBand || undefined,
        search: search || undefined,
      }),
  });

  const approveMutation = useMutation({
    mutationFn: approveRecord,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["records"] }),
  });
  const rejectMutation = useMutation({
    mutationFn: (id: string) => rejectRecord(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["records"] }),
  });
  const bulkApproveMutation = useMutation({
    mutationFn: () => bulkApprove({ source_id: sourceId || "all", min_confidence: 70 }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["records"] }),
  });

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

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All sources</option>
          {sources?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
          ))}
        </select>
        <select
          value={recordType}
          onChange={(e) => setRecordType(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All types</option>
          {["artist", "event", "exhibition", "venue", "artwork"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          {["pending", "approved", "rejected", "exported"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={confidenceBand}
          onChange={(e) => setConfidenceBand(e.target.value)}
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
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search title..."
          className="border border-gray-300 rounded px-2 py-1.5 text-sm flex-1 min-w-[200px]"
        />
      </div>

      {/* Records grid */}
      {isLoading && <div className="text-gray-400 text-center py-8">Loading...</div>}
      <div className="grid grid-cols-3 gap-4">
        {data?.items.map((record) => (
          <div key={record.id} className="bg-white border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            {record.primary_image_url && (
              <div className="h-40 bg-gray-100">
                <ImageThumbnail url={record.primary_image_url} alt={record.title ?? ""} className="w-full h-full" />
              </div>
            )}
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <RecordTypeBadge type={record.record_type} />
                <ConfidenceBadge
                  band={record.confidence_band as "HIGH" | "MEDIUM" | "LOW"}
                  score={record.confidence_score}
                />
              </div>
              <div className="font-medium text-sm leading-tight">
                {truncate(record.title ?? "Untitled", 60)}
              </div>
              {record.venue_name && (
                <div className="text-xs text-gray-500">{record.venue_name}</div>
              )}
              <StatusBadge status={record.status} />
              <div className="flex gap-1 pt-1">
                <button
                  onClick={() => approveMutation.mutate(record.id)}
                  className="flex-1 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                >
                  Approve
                </button>
                <button
                  onClick={() => rejectMutation.mutate(record.id)}
                  className="flex-1 py-1 border border-red-300 text-red-600 rounded text-xs hover:bg-red-50"
                >
                  Reject
                </button>
                <button
                  onClick={() => navigate(`/records/${record.id}`)}
                  className="flex-1 py-1 border border-gray-300 rounded text-xs hover:bg-gray-50"
                >
                  Edit
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {!isLoading && data?.items.length === 0 && (
        <div className="text-center text-gray-400 py-12">No records found.</div>
      )}
    </div>
  );
}
