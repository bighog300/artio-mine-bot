import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  applySourceMappingPreset,
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
  getSourceRuntimeMap,
  publishSourceMappingDraft,
  rollbackSourceMappingVersion,
  startMining,
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
import { Button, useToast } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";

export function SourceMapping() {
  const isMobile = useIsMobile();
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const draftIdFromUrl = searchParams.get("draft");
  const [localDraftId, setLocalDraftId] = useState<string | null>(draftIdFromUrl);
  const draftId = localDraftId ?? draftIdFromUrl;
  const [sampleRunId, setSampleRunId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);
  const [settings, setSettings] = useState({
    max_pages: 50,
    max_depth: 3,
    sample_pages_per_type: 5,
    discovery_roots: [] as string[],
    blocked_paths: [] as string[],
  });
  const [createPresetOpen, setCreatePresetOpen] = useState(false);
  const [deletingPresetId, setDeletingPresetId] = useState<string | null>(null);
  const [applyingPresetId, setApplyingPresetId] = useState<string | null>(null);

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
  const { data: runtimeMapState } = useQuery({
    queryKey: ["source-runtime-map", id],
    queryFn: () => getSourceRuntimeMap(id!),
    enabled: !!id,
  });

  const createDraftMutation = useMutation({
    mutationFn: () => createSourceMappingDraft(id!, { scan_mode: "standard", ...settings }),
    onMutate: () => ({ toastId: toast.loading("Creating mapping draft...") }),
    onSuccess: (payload, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      toast.success("Mapping draft queued", "Scan has been queued and will run in the background.");
      setLocalDraftId(payload.id);
      setSearchParams({ draft: payload.id });
      setMessage("Scan draft created.");
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, payload.id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, payload.id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-page-types", id, payload.id] });
    },
    onError: (e: Error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      toast.error("Failed to create mapping draft", e.message);
      setMessage(e.message);
    },
    onSettled: (_data, _error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
    },
  });

  const scanMutation = useMutation({
    mutationFn: () => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return startSourceMappingScan(id!, draftId);
    },
    onSuccess: (payload) => {
      setMessage(payload.message);
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-page-types", id, draftId] });
    },
    onError: (e: Error) => {
      toast.error("Failed to run scan", e.message);
      setMessage(e.message);
    },
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
    }) => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return updateSourceMappingRow(id!, draftId, rowId, updates);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] }),
    onError: (e: Error) => setMessage(e.message),
  });

  const actionMutation = useMutation({
    mutationFn: ({ rowIds, action }: { rowIds: string[]; action: "approve" | "reject" | "ignore" }) => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return applySourceMappingAction(id!, draftId, rowIds, action);
    },
    onSuccess: (payload) => {
      setMessage(`Bulk action '${payload.action}' updated ${payload.updated} row(s).`);
      qc.invalidateQueries({ queryKey: ["source-mapping-rows", id, draftId] });
      qc.invalidateQueries({ queryKey: ["source-mapping-draft", id, draftId] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const sampleRunMutation = useMutation({
    mutationFn: () => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return startSourceMappingSampleRun(id!, draftId, { sample_count: 5 });
    },
    onSuccess: (payload) => {
      setSampleRunId(payload.sample_run_id);
      setMessage(`Sample run ${payload.sample_run_id} ${payload.status}.`);
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const publishMutation = useMutation({
    mutationFn: () => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return publishSourceMappingDraft(id!, draftId);
    },
    onSuccess: (payload) => {
      setMessage(`Draft published at ${new Date(payload.published_at).toLocaleString()}.`);
      qc.invalidateQueries({ queryKey: ["source", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-versions", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-diff", id, draftId] });
    },
    onError: (e: Error) => {
      toast.error("Failed to publish draft", e.message);
      setMessage(e.message);
    },
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
    mutationFn: (payload: { name: string; description?: string; include_statuses: string[] }) => {
      if (!draftId) throw new Error("No active draft — create or open a draft first");
      return createSourceMappingPreset(id!, { ...payload, draft_id: draftId });
    },
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

  const applyPresetMutation = useMutation({
    mutationFn: (presetId: string) => applySourceMappingPreset(id!, presetId),
    onSuccess: () => {
      setMessage("Preset applied to runtime map.");
      qc.invalidateQueries({ queryKey: ["source", id] });
      qc.invalidateQueries({ queryKey: ["source-mapping-presets", id] });
    },
    onError: (e: Error) => {
      toast.error("Failed to apply preset", e.message);
      setMessage(e.message);
    },
    onSettled: () => setApplyingPresetId(null),
  });

  const startMiningMutation = useMutation({
    mutationFn: () => startMining(id!),
    onSuccess: (payload) => {
      toast.success("Mining started", `Job ${payload.job_id} is queued.`);
      setMessage("Mining job queued.");
      qc.invalidateQueries({ queryKey: ["source", id] });
    },
    onError: (e: Error) => {
      toast.error("Failed to start mining", e.message);
      setMessage(e.message);
    },
  });

  const rowItems = rows?.items ?? [];
  const assignTargetTypeToPageRole = async (pageTypeId: string, targetType: string) => {
    if (!draftId || !rowItems.length) return;
    const matchingRows = rowItems.filter((row) => row.page_type_id === pageTypeId);
    if (!matchingRows.length) return;
    await Promise.all(
      matchingRows.map((row) =>
        updateRowMutation.mutateAsync({
          rowId: row.id,
          updates: {
            destination_entity: targetType,
            destination_field: "title",
            status: "needs_review",
          },
        })
      )
    );
    setMessage(`Assigned '${targetType}' target type to ${matchingRows.length} row(s).`);
  };
  const selectedCount = selectedRowIds.length;
  const hasDraft = Boolean(draftId && draft);
  const approvedRowsCount = draft?.approved_count ?? 0;
  const needsReviewCount = draft?.needs_review_count ?? 0;
  const hasRows = rowItems.length > 0;
  const scanComplete = draft?.scan_status === "completed";
  const hasApprovedRows = approvedRowsCount > 0;
  const hasPublishedVersion = Boolean(source?.published_mapping_version_id);
  const hasAppliedPreset = Boolean(source?.active_mapping_preset_id);
  const crawlPlan = runtimeMapState?.runtime_map?.crawl_plan;
  const runtimeMapPhases = crawlPlan && typeof crawlPlan === "object" && "phases" in crawlPlan ? (crawlPlan as { phases?: unknown }).phases : undefined;
  const hasValidCrawlPlan = Array.isArray(runtimeMapPhases) && runtimeMapPhases.length > 0;
  const runtimeMap = runtimeMapState?.runtime_map;
  const hasExtractionRules = Boolean(runtimeMap && typeof runtimeMap === "object" && "extraction_rules" in runtimeMap && runtimeMap.extraction_rules && typeof runtimeMap.extraction_rules === "object" && Object.keys(runtimeMap.extraction_rules as Record<string, unknown>).length > 0);
  const hasMiningMap = Boolean(runtimeMap && typeof runtimeMap === "object" && "mining_map" in runtimeMap && runtimeMap.mining_map && typeof runtimeMap.mining_map === "object" && Object.keys(runtimeMap.mining_map as Record<string, unknown>).length > 0);
  const hasUsableRuntimeMap = hasValidCrawlPlan && (hasExtractionRules || hasMiningMap);
  const readyToMine = hasUsableRuntimeMap && (hasPublishedVersion || hasAppliedPreset);
  const readyForSampleRun = hasDraft && scanComplete && hasApprovedRows;
  const readyForPublish = hasDraft && scanComplete && hasApprovedRows;
  const canStartMining = readyToMine;
  const canRunScan = hasDraft;
  const canRunSample = readyForSampleRun;
  const canPublishDraft = readyForPublish;
  const settingsValidationMessage = useMemo(() => {
    if (settings.max_pages <= 0) return "Max pages must be greater than 0.";
    if (settings.max_depth <= 0) return "Max depth must be greater than 0.";
    if (settings.sample_pages_per_type <= 0) return "Samples per type must be greater than 0.";
    return null;
  }, [settings.max_depth, settings.max_pages, settings.sample_pages_per_type]);
  const nextStepMessage = useMemo(() => {
    if (!hasDraft) return "Next step: run scan by creating a draft.";
    if (!scanComplete) return "Next step: wait for scan completion and then review rows.";
    if (!hasRows) return "Next step: re-scan with broader settings to generate mapping rows.";
    if (!hasApprovedRows) return "Next step: review and approve rows.";
    if (!sampleRun) return "Next step: run sample extraction (recommended) before publishing.";
    if (!hasPublishedVersion) return "Next step: publish draft.";
    if (!hasAppliedPreset) return "Next step: apply a preset so runtime mapping stays explicit.";
    if (!hasUsableRuntimeMap) return "Next step: fix runtime mapping payload before mining.";
    return "Next step: start mining.";
  }, [hasAppliedPreset, hasApprovedRows, hasDraft, hasPublishedVersion, hasRows, hasUsableRuntimeMap, sampleRun, scanComplete]);
  const mineDisabledReason = !hasDraft
    ? "Create and complete a mapping draft first."
    : !scanComplete
      ? "Complete the mapping scan before mining."
      : !hasPublishedVersion && !hasAppliedPreset
        ? "Publish a draft or apply a preset before starting mining."
        : !hasValidCrawlPlan
          ? "Runtime mapping is missing crawl_plan.phases."
          : !hasExtractionRules && !hasMiningMap
            ? "Runtime mapping has no extraction/mining rules."
            : null;
  const sampleDisabledReason = !hasDraft
    ? "Create a mapping draft first."
    : !scanComplete
      ? "Complete scan before running sample extraction."
      : !hasApprovedRows
        ? "Approve at least one row before running sample extraction."
        : null;
  const publishDisabledReason = !hasDraft
    ? "Create a mapping draft first."
    : !scanComplete
      ? "Complete scan before publishing."
      : !hasApprovedRows
        ? "Approve at least one mapping row before publishing."
        : null;
  const publishReadinessSummary = `Readiness — approved: ${approvedRowsCount}, needs review: ${needsReviewCount}. Sample run is recommended before publish.`;
  const filteredRows = useMemo(
    () => rowItems.filter((row) => (statusFilter === "all" ? true : row.status === statusFilter)),
    [rowItems, statusFilter]
  );

  if (!id) return <div className="p-6">Missing source ID.</div>;

  return (
    <div className="space-y-4 lg:space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/sources/${id}`)}>← Back to source</Button>
        <h1 className="text-2xl lg:text-3xl font-bold">Source Mapping Workflow</h1>
        <p className="text-sm text-muted-foreground">{source?.url ?? "Loading source..."}</p>
        <p className="text-xs text-muted-foreground mt-1">
          Workflow: create draft → scan and moderate rows → sample extraction moderation → publish/apply preset → mine.
        </p>
      </div>
      <section className="rounded border bg-card p-4">
        <h2 className="font-semibold">Workflow status</h2>
        <p className="text-sm mt-1">{nextStepMessage}</p>
        <p className="text-xs text-muted-foreground mt-1">
          Draft: {hasDraft ? "yes" : "no"} · Scan complete: {scanComplete ? "yes" : "no"} · Rows: {rowItems.length} · Approved: {approvedRowsCount} · Needs review: {needsReviewCount} · Runtime map ready: {hasUsableRuntimeMap ? "yes" : "no"}.
        </p>
      </section>

      {message && <div className="rounded border border-border bg-muted/40 px-3 py-2 text-sm">{message}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ScanSetupForm
          sourceUrl={source?.url ?? ""}
          settings={settings}
          onSettingsChange={setSettings}
          onCreateDraft={() => createDraftMutation.mutate()}
          onRunScan={draftId ? () => scanMutation.mutate() : undefined}
          loading={createDraftMutation.isPending}
          scanLoading={scanMutation.isPending}
          disableRunScan={!canRunScan}
          runScanDisabledReason={!canRunScan ? "Create a mapping draft first before re-scan." : null}
          settingsValidationMessage={settingsValidationMessage}
        />
        <section className="rounded border bg-card p-4 space-y-2 text-sm">
          <h2 className="font-semibold">Scan Status</h2>
          {!draft ? <p className="text-muted-foreground">No scan draft yet.</p> : (
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
        <PageTypeSidebar
          pageTypes={pageTypes?.items ?? []}
          onAssignTargetType={assignTargetTypeToPageRole}
        />
        <MappingPreviewPanel preview={preview} />
        <SampleRunReview
          sampleRun={sampleRun}
          onStart={() => sampleRunMutation.mutate()}
          loading={sampleRunMutation.isPending}
          disabled={!canRunSample}
          disabledReason={sampleDisabledReason}
          onModerateResult={(resultId, payload) => moderateSampleResultMutation.mutate({ resultId, payload })}
        />
      </div>

      <MappingPresetPanel
        presets={presets?.items ?? []}
        loading={presetsLoading}
        deletingPresetId={deletingPresetId}
        applyingPresetId={applyingPresetId}
        canCreate={!!draftId}
        onOpenCreate={() => setCreatePresetOpen(true)}
        onApply={(presetId) => {
          setApplyingPresetId(presetId);
          applyPresetMutation.mutate(presetId);
        }}
        onDelete={(presetId) => {
          if (!window.confirm("Delete this preset? This cannot be undone.")) return;
          setDeletingPresetId(presetId);
          deletePresetMutation.mutate(presetId);
        }}
      />

      <div>
        <Button
          onClick={() => startMiningMutation.mutate()}
          loading={startMiningMutation.isPending}
          disabled={!canStartMining}
          title={!canStartMining ? mineDisabledReason ?? undefined : undefined}
        >
          Start Mining
        </Button>
        {!canStartMining && mineDisabledReason ? <p className="text-xs text-muted-foreground mt-1">{mineDisabledReason}</p> : null}
      </div>

      {selectedCount > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "approve" })}>Bulk approve ({selectedCount})</Button>
          <Button fullWidth={isMobile} size="sm" variant="danger" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "reject" })}>Bulk reject</Button>
          <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => actionMutation.mutate({ rowIds: selectedRowIds, action: "ignore" })}>Bulk ignore</Button>
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
        canPublish={canPublishDraft}
        publishDisabledReason={publishDisabledReason}
        readinessSummary={publishReadinessSummary}
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
