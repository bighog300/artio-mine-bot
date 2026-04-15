import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  applySourceMappingAction,
  createSourceMappingDraft,
  getSource,
  getSourceMappingDraft,
  getSourceMappingPreview,
  getSourceMappingRows,
  updateSourceMappingRow,
} from "@/lib/api";

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

  const rowCount = rows?.items.length ?? 0;

  const updateRowMutation = useMutation({
    mutationFn: ({ rowId, status }: { rowId: string; status: string }) =>
      updateSourceMappingRow(id!, draftId!, rowId, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] }),
    onError: (e: Error) => setMessage(e.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ rowId, action }: { rowId: string; action: "approve" | "reject" }) =>
      applySourceMappingAction(id!, draftId!, [rowId], action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] }),
    onError: (e: Error) => setMessage(e.message),
  });

  const selectedSampleId = useMemo(() => (rowCount > 0 ? "default" : null), [rowCount]);

  const { data: preview } = useQuery({
    queryKey: ["source-mapping-preview", id, draftId, selectedSampleId],
    queryFn: () => getSourceMappingPreview(id!, draftId!, selectedSampleId!),
    enabled: !!id && !!draftId && !!selectedSampleId,
  });

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
            </ul>
          ) : <p className="text-sm text-gray-500">No scan draft yet.</p>}
        </section>
      </div>

      <section className="rounded border bg-white p-4">
        <h2 className="font-semibold mb-3">Mapping Matrix</h2>
        {!rows?.items.length ? (
          <p className="text-sm text-gray-500">No mapping rows yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2">Selector</th>
                <th className="text-left p-2">Sample</th>
                <th className="text-left p-2">Destination</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.items.map((row) => (
                <tr key={row.id} className="border-t">
                  <td className="p-2">{row.selector}</td>
                  <td className="p-2">{row.sample_value ?? "—"}</td>
                  <td className="p-2">{row.destination_entity}.{row.destination_field}</td>
                  <td className="p-2">
                    <select className="border rounded px-2 py-1" value={row.status} onChange={(e) => updateRowMutation.mutate({ rowId: row.id, status: e.target.value })}>
                      <option value="proposed">proposed</option>
                      <option value="needs_review">needs_review</option>
                      <option value="approved">approved</option>
                      <option value="rejected">rejected</option>
                    </select>
                  </td>
                  <td className="p-2 space-x-2">
                    <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowId: row.id, action: "approve" })}>Approve</button>
                    <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowId: row.id, action: "reject" })}>Reject</button>
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
              <ul className="mt-2 list-disc pl-5">
                {preview.extractions.map((item) => (
                  <li key={item.mapping_row_id}>{item.destination_field}: {item.normalized_value ?? "(empty)"}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-medium">Record preview</div>
              <pre className="bg-gray-50 border rounded p-2 overflow-auto">{JSON.stringify(preview.record_preview, null, 2)}</pre>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
