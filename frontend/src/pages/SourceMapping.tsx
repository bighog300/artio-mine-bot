import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  applySourceMappingAction,
  createSourceMappingPreset,
  createSourceMappingDraft,
  deleteSourceMappingPreset,
  getSource,
  getSourceMappingDiff,
  getSourceMappingDraft,
  getSourceMappingPageTypes,
  getSourceMappingPresets,
  getSourceMappingPreview,
  getSourceMappingRows,
  getSourceMappingSampleRun,
  getSourceMappingVersions,
  publishSourceMappingDraft,
  rollbackSourceMappingVersion,
  startSourceMappingSampleRun,
  startSourceMappingScan,
  updateSourceMappingSampleRunResult,
  updateSourceMappingRow,
} from "@/lib/api";
import { MappingMatrix } from "@/components/source-mapper/MappingMatrix";
import { MappingPresetPanel } from "@/components/source-mapper/MappingPresetPanel";
import { MappingPreviewPanel } from "@/components/source-mapper/MappingPreviewPanel";
import { PageTypeSidebar } from "@/components/source-mapper/PageTypeSidebar";
import { SampleRunReview } from "@/components/source-mapper/SampleRunReview";
import { ScanSetupForm } from "@/components/source-mapper/ScanSetupForm";
import { VersionHistoryPanel } from "@/components/source-mapper/VersionHistoryPanel";
import { CreatePresetDialog } from "@/components/source-mapper/CreatePresetDialog";

export function SourceMapping() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [draftId, setDraftId] = useState<string | null>(null);
  const [sampleRunId, setSampleRunId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);
  const [settings, setSettings] = useState({ max_pages: 50, max_depth: 3, sample_pages_per_type: 5 });
  const [createPresetOpen, setCreatePresetOpen] = useState(false);
  const [deletingPresetId, setDeletingPresetId] = useState<string | null>(null);

  useEffect(() => {
    const draftFromUrl = searchParams.get("draft");
    if (draftFromUrl && !draftId) {
      setDraftId(draftFromUrl);
    }
  }, [searchParams, draftId]);

  const { data: source } = useQuery({ queryKey: ["source", id], queryFn: () => getSource(id!), enabled: !!id });
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
  const { data: pageTypes } = useQuery({
    queryKey: ["source-mapping-page-types", id, draftId],
    queryFn: () => getSourceMappingPageTypes(id!, draftId!),
    enabled: !!id && !!draftId,
  });
  const { data: preview } = useQuery({
    queryKey: ["source-mapping-preview", id, draftId],
    queryFn: () => getSourceMappingPreview(id!, draftId!, "default"),
    enabled: !!id && !!draftId,
  });
  const { data: versions } = useQuery({
    queryKey: ["source-mapping-versions", id],
    queryFn: () => getSourceMappingVersions(id!),
    enabled: !!id,
  });
  const { data: diff } = useQuery({
    queryKey: ["source-mapping-diff", id, draftId],
    queryFn: () => getSourceMappingDiff(id!, draftId!),
    enabled: !!id && !!draftId,
  });
  const { data: presets, isLoading: presetsLoading } = useQuery({
    queryKey: ["source-mapping-presets", id],
    queryFn: () => getSourceMappingPresets(id!),
    enabled: !!id,
  });
  const { data: sampleRun } = useQuery({
    queryKey: ["source-mapping-sample-run", id, draftId, sampleRunId],
    queryFn: () => getSourceMappingSampleRun(id!, draftId!, sampleRunId!),
    enabled: !!id && !!draftId && !!sampleRunId,
  });

  const createDraftMutation = useMutation({
    mutationFn: () => createSourceMappingDraft(id!, { scan_mode: "standard", ...settings }),
    onSuccess: (payload) => {
      setDraftId(payload.id);
      setMessage("Scan draft created.");
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, payload.id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, payload.id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-page-types", id, payload.id] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const scanMutation = useMutation({
    mutationFn: () => startSourceMappingScan(id!, draftId!),
    onSuccess: (payload) => {
      setMessage(payload.message);
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-page-types", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const updateRowMutation = useMutation({
    mutationFn: ({
      rowId,
      updates,
    }: {
      rowId: string;
      updates: {
        status?: string;
        destination_entity?: string;
        destination_field?: string;
        category_target?: string | null;
      };
    }) => updateSourceMappingRow(id!, draftId!, rowId, updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] }),
    onError: (e: Error) => setMessage(e.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ rowIds, action }: { rowIds: string[]; action: "approve" | "reject" | "ignore" }) =>
      applySourceMappingAction(id!, draftId!, rowIds, action),
    onSuccess: (payload) => {
      setMessage(`Bulk action '${payload.action}' updated ${payload.updated} row(s).`);
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const sampleRunMutation = useMutation({
    mutationFn: () => startSourceMappingSampleRun(id!, draftId!, { sample_count: 5 }),
    onSuccess: (payload) => {
      setSampleRunId(payload.sample_run_id);
      setMessage(`Sample run ${payload.sample_run_id} ${payload.status}.`);
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishSourceMappingDraft(id!, draftId!),
    onSuccess: (payload) => {
      setMessage(`Draft published at ${new Date(payload.published_at).toLocaleString()}.`);
      qc.invalidateQueries({ queryKey: ["source", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-versions", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-diff", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const moderateSampleResultMutation = useMutation({
    mutationFn: ({
      resultId,
      payload,
    }: {
      resultId: string;
      payload: { review_status?: string; review_notes?: string };
    }) => updateSourceMappingSampleRunResult(id!, draftId!, sampleRunId!, resultId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["source-mapping-sample-run", id, draftId, sampleRunId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const rollbackMutation = useMutation({
    mutationFn: (versionId: string) => rollbackSourceMappingVersion(id!, versionId),
    onSuccess: (payload) => {
      setMessage(`Rolled back to version ${payload.id}.`);
      qc.invalidateQueries({ queryKey: ["source", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-versions", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-diff", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const createPresetMutation = useMutation({
    mutationFn: (payload: { name: string; description?: string; include_statuses: string[] }) =>
      createSourceMappingPreset(id!, { ...payload, draft_id: draftId! }),
    onSuccess: (payload) => {
      setMessage(`Preset '${payload.name}' created.`);
      setCreatePresetOpen(false);
      qc.invalidateQueries({ queryKey: ["source-mapping-presets", id] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const deletePresetMutation = useMutation({
    mutationFn: (presetId: string) => deleteSourceMappingPreset(id!, presetId),
    onSuccess: () => {
      setMessage("Preset deleted.");
      qc.invalidateQueries({ queryKey: ["source-mapping-presets", id] });
    },
    onError: (e: Error) => setMessage(e.message),
    onSettled: () => setDeletingPresetId(null),
  });

  const rowItems = rows?.items ?? [];
  const selectedCount = selectedRowIds.length;
  const filteredRows = useMemo(
    () => rowItems.filter((row) => (statusFilter === "all" ? true : row.status === statusFilter)),
    [rowItems, statusFilter]
  );

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
        <ScanSetupForm
          sourceUrl={source?.url ?? ""}
          settings={settings}
          onSettingsChange={setSettings}
          onCreateDraft={() => createDraftMutation.mutate()}
          onRunScan={draftId ? () => scanMutation.mutate() : undefined}
          loading={createDraftMutation.isPending}
          scanLoading={scanMutation.isPending}
        />
        <section className="rounded border bg-white p-4 space-y-2 text-sm">
          <h2 className="font-semibold">Scan Status</h2>
          {!draft ? <p className="text-gray-500">No scan draft yet.</p> : (
            <ul className="space-y-1">
              <li>Status: <strong>{draft.scan_status}</strong></li>
              <li>Progress: <strong>{draft.scan_progress_percent}%</strong>{draft.scan_stage ? ` (${draft.scan_stage})` : ""}</li>
              <li>Rows: <strong>{draft.mapping_count}</strong></li>
              <li>Approved: <strong>{draft.approved_count}</strong></li>
              <li>Needs review: <strong>{draft.needs_review_count}</strong></li>
              <li>Changed from published: <strong>{draft.changed_from_published_count}</strong></li>
            </ul>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <PageTypeSidebar pageTypes={pageTypes?.items ?? []} />
        <MappingPreviewPanel preview={preview} />
        <SampleRunReview
          sampleRun={sampleRun}
          onStart={() => sampleRunMutation.mutate()}
          loading={sampleRunMutation.isPending}
          onModerateResult={(resultId, payload) => moderateSampleResultMutation.mutate({ resultId, payload })}
        />
      </div>

      <MappingPresetPanel
        presets={presets?.items ?? []}
        loading={presetsLoading}
        deletingPresetId={deletingPresetId}
        canCreate={!!draftId}
        onOpenCreate={() => setCreatePresetOpen(true)}
        onDelete={(presetId) => {
          if (!window.confirm("Delete this preset? This cannot be undone.")) return;
          setDeletingPresetId(presetId);
          deletePresetMutation.mutate(presetId);
        }}
      />

      {selectedCount > 0 && (
        <div className="flex gap-2 text-xs">
          <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "approve" })}>Bulk approve ({selectedCount})</button>
          <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "reject" })}>Bulk reject</button>
          <button className="px-2 py-1 border rounded" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "ignore" })}>Bulk ignore</button>
        </div>
      )}

      <MappingMatrix
        rows={filteredRows}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        selectedRowIds={selectedRowIds}
        setSelectedRowIds={setSelectedRowIds}
        onRowUpdate={(rowId, updates) => updateRowMutation.mutate({ rowId, updates })}
      />

      <VersionHistoryPanel
        versions={versions?.items ?? []}
        diff={diff}
        onPublish={() => publishMutation.mutate()}
        publishing={publishMutation.isPending}
        onRollback={(versionId) => rollbackMutation.mutate(versionId)}
      />

      {draftId ? (
        <CreatePresetDialog
          open={createPresetOpen}
          draftId={draftId}
          creating={createPresetMutation.isPending}
          onClose={() => setCreatePresetOpen(false)}
          onCreate={(payload) => createPresetMutation.mutate(payload)}
        />
      ) : null}
    </div>
  );
}
