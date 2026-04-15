import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  applySourceMappingAction,
  createSourceMappingDraft,
  getSource,
  getSourceMappingDiff,
  getSourceMappingDraft,
  getSourceMappingPreview,
  getSourceMappingRows,
  getSourceMappingVersions,
  publishSourceMappingDraft,
  updateSourceMappingRow,
} from "@/lib/api";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";

export function SourceMapping() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [draftId, setDraftId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [settings, setSettings] = useState({
    max_pages: 50,
    max_depth: 3,
    sample_pages_per_type: 5,
  });
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);
  const [bulkEntity, setBulkEntity] = useState("event");
  const [bulkField, setBulkField] = useState("title");
  const [forceLowConfidence, setForceLowConfidence] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: source } = useQuery({ queryKey: ["source", id], queryFn: () => getSource(id!), enabled: !!id });

  const createDraftMutation = useMutation({
    mutationFn: async () =>
      createSourceMappingDraft(id!, {
        scan_mode: "standard",
        max_pages: settings.max_pages,
        max_depth: settings.max_depth,
        sample_pages_per_type: settings.sample_pages_per_type,
      }),
    onSuccess: (draft) => {
      setDraftId(draft.id);
      setMessage("Scan draft created.");
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draft.id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draft.id] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const { data: draft } = useQuery({
    queryKey: ["source-mapping-draft", id, draftId],
    queryFn: () => getSourceMappingDraft(id!, draftId!),
    enabled: !!id && !!draftId,
    refetchInterval: 4000,
  });

  const { data: rows } = useQuery({
    queryKey: ["source-mapping-rows", id, draftId],
    queryFn: () => getSourceMappingRows(id!, draftId!),
    enabled: !!id && !!draftId,
  });
  const filteredRows = useMemo(
    () => rows?.items.filter((row) => (statusFilter === "all" ? true : row.status === statusFilter)) ?? [],
    [rows?.items, statusFilter]
  );

  const rowCount = rows?.items.length ?? 0;

  const updateRowMutation = useMutation({
    mutationFn: ({ rowId, status }: { rowId: string; status: string }) =>
      updateSourceMappingRow(id!, draftId!, rowId, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] }),
    onError: (e: Error) => setMessage(e.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({
      rowIds,
      action,
      opts,
    }: {
      rowIds: string[];
      action: "approve" | "reject" | "ignore" | "disable" | "enable" | "needs_review" | "move_destination";
      opts?: { destination_entity?: string; destination_field?: string; force_low_confidence?: boolean };
    }) =>
      applySourceMappingAction(id!, draftId!, rowIds, action, opts),
    onSuccess: (payload) => {
      setMessage(`Bulk action "${payload.action}" updated ${payload.updated} row(s).`);
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-diff", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const { data: versions } = useQuery({
    queryKey: ["source-mapping-versions", id],
    queryFn: () => getSourceMappingVersions(id!),
    enabled: !!id,
  });

  const publishMutation = useMutation({
    mutationFn: () => publishSourceMappingDraft(id!, draftId!),
    onSuccess: (payload) => {
      setMessage(`Draft published at ${new Date(payload.published_at).toLocaleString()}.`);
      qc.invalidateQueries({ queryKey: ["source", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-versions", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const selectedSampleId = useMemo(() => (rowCount > 0 ? "default" : null), [rowCount]);

  const { data: preview } = useQuery({
    queryKey: ["source-mapping-preview", id, draftId, selectedSampleId],
    queryFn: () => getSourceMappingPreview(id!, draftId!, selectedSampleId!),
    enabled: !!id && !!draftId && !!selectedSampleId,
  });

  const { data: diff } = useQuery({
    queryKey: ["source-mapping-diff", id, draftId],
    queryFn: () => getSourceMappingDiff(id!, draftId!),
    enabled: !!id && !!draftId,
  });

  const selectedCount = selectedRowIds.length;
  const allVisibleSelected = filteredRows.length > 0 && filteredRows.every((row) => selectedRowIds.includes(row.id));
  const toggleSelected = (rowId: string, enabled: boolean) => {
    setSelectedRowIds((current) => {
      if (enabled) return current.includes(rowId) ? current : [...current, rowId];
      return current.filter((id) => id !== rowId);
    });
  };

  if (!id) return <div className="p-6">Missing source ID.</div>;

  return (
    <div className="space-y-4">
      <div>
        <button onClick={() => navigate(`/sources/${id}`)} className="text-sm text-gray-500 hover:text-gray-700">← Back to source</button>
        <h1 className="text-2xl font-bold">AI Source Mapper</h1>
        <p className="text-sm text-gray-500">{source?.url ?? "Loading source..."}</p>
      </div>

      {message && <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm">{message}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded border bg-white p-4 space-y-3">
          <h2 className="font-semibold">URL Input & Scan Settings</h2>
          <input className="w-full border rounded px-3 py-2 text-sm" value={source?.url ?? ""} disabled />
          <div className="grid grid-cols-3 gap-2 text-sm">
            <label className="space-y-1">Max pages
              <input type="number" className="w-full border rounded px-2 py-1" value={settings.max_pages} onChange={(e) => setSettings((s) => ({ ...s, max_pages: Number(e.target.value || 0) }))} />
            </label>
            <label className="space-y-1">Max depth
              <input type="number" className="w-full border rounded px-2 py-1" value={settings.max_depth} onChange={(e) => setSettings((s) => ({ ...s, max_depth: Number(e.target.value || 0) }))} />
            </label>
            <label className="space-y-1">Samples/type
              <input type="number" className="w-full border rounded px-2 py-1" value={settings.sample_pages_per_type} onChange={(e) => setSettings((s) => ({ ...s, sample_pages_per_type: Number(e.target.value || 0) }))} />
            </label>
          </div>
          <button className="px-3 py-2 bg-blue-600 text-white rounded disabled:opacity-60" onClick={() => createDraftMutation.mutate()} disabled={createDraftMutation.isPending}>
            {createDraftMutation.isPending ? "Creating..." : "Create Source Scan"}
          </button>
        </section>

        <section className="rounded border bg-white p-4 space-y-2">
          <h2 className="font-semibold">Scan Status</h2>
          {draft ? (
            <ul className="text-sm space-y-1">
              <li>Status: <strong>{draft.scan_status}</strong></li>
              <li>Rows: <strong>{draft.mapping_count}</strong></li>
              <li>Approved: <strong>{draft.approved_count}</strong></li>
              <li>Needs review: <strong>{draft.needs_review_count}</strong></li>
              <li>Changed vs published: <strong>{draft.changed_from_published_count}</strong></li>
            </ul>
          ) : <p className="text-sm text-gray-500">No scan draft yet.</p>}
        </section>
      </div>

      <section className="rounded border bg-white p-4 space-y-2">
        <h2 className="font-semibold">Versioning & Publish</h2>
        {draftId ? (
          <>
            <div className="text-sm">
              {diff ? (
                <span>
                  Diff summary — Added: <strong>{diff.added}</strong>, Changed: <strong>{diff.changed}</strong>, Removed: <strong>{diff.removed}</strong>, Unchanged: <strong>{diff.unchanged}</strong>
                </span>
              ) : "Loading diff..."}
            </div>
            <button
              className="px-3 py-2 bg-emerald-600 text-white rounded disabled:opacity-60"
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
            >
              {publishMutation.isPending ? "Publishing..." : "Publish Draft"}
            </button>
          </>
        ) : <p className="text-sm text-gray-500">Create a draft to enable versioning and publish actions.</p>}
        <div className="text-sm">
          <div className="font-medium mb-1">Recent versions</div>
          {!versions?.items.length ? "No versions yet." : (
            <ul className="space-y-1">
              {versions.items.slice(0, 4).map((version) => (
                <li key={version.id} className="text-xs">
                  v{version.version_number} — <strong>{version.status}</strong> {version.published_at ? `(published ${new Date(version.published_at).toLocaleString()})` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="rounded border bg-white p-4">
        <h2 className="font-semibold mb-3">Mapping Matrix</h2>
        <div className="mb-3 grid grid-cols-1 gap-2 lg:grid-cols-3 text-sm">
          <label className="space-y-1">
            <span>Status filter</span>
            <select className="w-full border rounded px-2 py-1" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">all</option>
              <option value="proposed">proposed</option>
              <option value="needs_review">needs_review</option>
              <option value="changed_from_published">changed_from_published</option>
              <option value="approved">approved</option>
              <option value="rejected">rejected</option>
              <option value="ignored">ignored</option>
            </select>
          </label>
          <label className="space-y-1">
            <span>Move destination entity</span>
            <input className="w-full border rounded px-2 py-1" value={bulkEntity} onChange={(e) => setBulkEntity(e.target.value)} />
          </label>
          <label className="space-y-1">
            <span>Move destination field</span>
            <input className="w-full border rounded px-2 py-1" value={bulkField} onChange={(e) => setBulkField(e.target.value)} />
          </label>
        </div>
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          <button className="px-2 py-1 border rounded" disabled={!selectedCount} onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "approve", opts: { force_low_confidence: forceLowConfidence } })}>Bulk approve ({selectedCount})</button>
          <button className="px-2 py-1 border rounded" disabled={!selectedCount} onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "reject" })}>Bulk reject</button>
          <button className="px-2 py-1 border rounded" disabled={!selectedCount} onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "ignore" })}>Bulk ignore</button>
          <button className="px-2 py-1 border rounded" disabled={!selectedCount} onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "move_destination", opts: { destination_entity: bulkEntity, destination_field: bulkField } })}>Move destination</button>
          <label className="inline-flex items-center gap-1 px-2 py-1 border rounded">
            <input type="checkbox" checked={forceLowConfidence} onChange={(e) => setForceLowConfidence(e.target.checked)} />
            Force low-confidence approve
          </label>
        </div>
        {!rows?.items.length ? (
          <p className="text-sm text-gray-500">No mapping rows yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2"><input type="checkbox" checked={allVisibleSelected} onChange={(e) => setSelectedRowIds(e.target.checked ? filteredRows.map((row) => row.id) : [])} /></th>
                <th className="text-left p-2">Selector</th>
                <th className="text-left p-2">Sample</th>
                <th className="text-left p-2">Destination</th>
                <th className="text-left p-2">Category</th>
                <th className="text-left p-2">Confidence</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, rowIndex) => (
                <tr key={row.id} className="border-t">
                  <td className="p-2 align-top"><input type="checkbox" checked={selectedRowIds.includes(row.id)} onChange={(e) => toggleSelected(row.id, e.target.checked)} /></td>
                  <td className="p-2">{row.selector}</td>
                  <td className="p-2">{row.sample_value ?? "—"}</td>
                  <td className="p-2">{row.destination_entity}.{row.destination_field}</td>
                  <td className="p-2">
                    <input
                      className="w-32 border rounded px-2 py-1"
                      value={row.category_target ?? ""}
                      placeholder="optional"
                      onBlur={(e) => updateRowMutation.mutate({ rowId: row.id, status: row.status })}
                      onChange={(e) => updateSourceMappingRow(id!, draftId!, row.id, { category_target: e.target.value || null })}
                    />
                  </td>
                  <td className="p-2">
                    <ConfidenceBadge band={row.confidence_band} score={Math.round(row.confidence_score * 100)} />
                    {row.low_confidence_blocked && <div className="text-xs text-amber-700 mt-1">approval blocked unless forced</div>}
                  </td>
                  <td className="p-2">
                    <select className="border rounded px-2 py-1" value={row.status} onChange={(e) => updateRowMutation.mutate({ rowId: row.id, status: e.target.value })}>
                      <option value="proposed">proposed</option>
                      <option value="needs_review">needs_review</option>
                      <option value="changed_from_published">changed_from_published</option>
                      <option value="approved">approved</option>
                      <option value="rejected">rejected</option>
                      <option value="ignored">ignored</option>
                    </select>
                  </td>
                  <td className="p-2 space-x-2">
                    <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowIds: [row.id], action: "approve", opts: { force_low_confidence: forceLowConfidence } })}>Approve</button>
                    <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowIds: [row.id], action: "reject" })}>Reject</button>
                    <button
                      className="px-2 py-1 border rounded"
                      disabled={rowIndex === 0}
                      onClick={() => actionMutation.mutate({ rowIds: [row.id], action: "move_destination", opts: { destination_entity: filteredRows[Math.max(0, rowIndex - 1)].destination_entity, destination_field: filteredRows[Math.max(0, rowIndex - 1)].destination_field } })}
                    >
                      Move ↑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="rounded border bg-white p-4">
        <h2 className="font-semibold mb-3">Preview Panel</h2>
        {!preview ? <p className="text-sm text-gray-500">Preview unavailable until a draft exists.</p> : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 text-sm">
            <div>
              <div className="font-medium">Sample page</div>
              <div className="text-gray-600 break-all">{preview.page_url}</div>
              {preview.source_snippet && <pre className="mt-2 bg-gray-50 border rounded p-2 overflow-auto whitespace-pre-wrap">{preview.source_snippet}</pre>}
              <ul className="mt-2 list-disc pl-5">
                {preview.extractions.map((item) => (
                  <li key={item.mapping_row_id}>{item.destination_field}: {item.normalized_value ?? "(empty)"} {item.warning ? <span className="text-amber-700">({item.warning})</span> : null}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-medium">Record preview</div>
              <pre className="bg-gray-50 border rounded p-2 overflow-auto">{JSON.stringify(preview.record_preview, null, 2)}</pre>
              <div className="font-medium mt-2">Category preview</div>
              <pre className="bg-gray-50 border rounded p-2 overflow-auto">{JSON.stringify(preview.category_preview, null, 2)}</pre>
              {preview.warnings.length > 0 ? (
                <ul className="mt-2 list-disc pl-5 text-amber-700">
                  {preview.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              ) : null}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
