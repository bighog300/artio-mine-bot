import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Eye, Pause, Play, RotateCcw, Sparkles, Square, Trash2 } from "lucide-react";
import {
  createSource,
  createSourceMappingDraft,
  deleteSource,
  getSources,
  mapSite,
  pauseSource,
  resumeSource,
  retryFailedSource,
  startMining,
  stopSource,
  type CreateSourceInput,
} from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { formatRelative } from "@/lib/utils";
import { Button, EmptyState, Input, Select, Skeleton, SkeletonTableRows, useToast } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";
import type { Source } from "@/lib/api";

type SourceAction = "start-discovery" | "start-full" | "pause" | "resume" | "stop" | "retry-failed";

const CRAWL_INTENT_OPTIONS: Array<{ value: CreateSourceInput["crawl_intent"]; label: string }> = [
  { value: "site_root", label: "Site root" },
  { value: "directory_listing", label: "Directory/listing page" },
  { value: "detail_entity", label: "Detail/entity page" },
  { value: "test_crawl", label: "Test crawl" },
];

export function Sources() {
  const isMobile = useIsMobile();
  const [showDialog, setShowDialog] = useState(false);
  const [form, setForm] = useState<CreateSourceInput>({
    url: "",
    name: "",
    crawl_intent: "site_root",
    enabled: true,
  });
  const [error, setError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();

  const { data, isLoading } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const createMutation = useMutation({
    mutationFn: createSource,
    onSuccess: () => {
      toast.success("Source created", "The source has been added successfully.");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
    },
    onError: (e: Error) => {
      setError(e.message);
      toast.error("Failed to create source", e.message);
    },
  });

  const createAndRunMutation = useMutation({
    mutationFn: async ({ action }: { action: "start-discovery" | "start-full" }) => {
      const source = await createSource(form);
      if (action === "start-discovery") {
        await mapSite(source.id);
      } else {
        await startMining(source.id);
      }
      return source;
    },
    onMutate: ({ action }) => ({
      toastId: toast.loading(action === "start-discovery" ? "Starting discovery..." : "Starting full mining..."),
    }),
    onSuccess: (_data, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      toast.success("Mining started", "Source saved and job started.");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setActionFeedback("Source saved and job started.");
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
    },
    onError: (e: Error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      setError(e.message);
      toast.error("Unable to start mining", e.message);
    },
    onSettled: (_data, _error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
    },
  });

  const createAndOpenMappingMutation = useMutation({
    mutationFn: async () => {
      const source = await createSource(form);
      const draft = await createSourceMappingDraft(source.id, {
        scan_mode: "standard",
        max_pages: form.max_pages ?? 50,
        max_depth: form.max_depth ?? 3,
      });
      return { sourceId: source.id, draftId: draft.id };
    },
    onMutate: () => ({ toastId: toast.loading("Creating mapping draft...") }),
    onSuccess: ({ sourceId, draftId }, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      toast.success("Mapping scan started", "Source saved and mapping scan started.");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setActionFeedback("Source saved and mapping scan started.");
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
      navigate(`/sources/${sourceId}/mapping?draft=${draftId}`);
    },
    onError: (e: Error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      setError(e.message);
      toast.error("Unable to open mapping", e.message);
    },
    onSettled: (_data, _error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSource,
    onMutate: () => ({ toastId: toast.loading("Deleting source...") }),
    onSuccess: (_data, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Source deleted");
    },
    onError: (e: Error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      toast.error("Delete failed", e.message);
    },
    onSettled: (_data, _error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
    },
  });

  const actionMutation = useMutation({
    onMutate: ({ action }) => ({ toastId: toast.loading(`Running ${action.replace("-", " ")}...`) }),
    mutationFn: async ({ sourceId, action }: { sourceId: string; action: SourceAction }) => {
      switch (action) {
        case "start-discovery":
          return mapSite(sourceId);
        case "start-full":
          return startMining(sourceId);
        case "pause":
          return pauseSource(sourceId);
        case "resume":
          return resumeSource(sourceId);
        case "stop":
          return stopSource(sourceId);
        case "retry-failed":
          return retryFailedSource(sourceId);
      }
    },
    onSuccess: (_data, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      setActionFeedback("Source action accepted.");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Source action accepted");
    },
    onError: (e: Error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
      setActionFeedback(e.message);
      toast.error("Source action failed", e.message);
    },
    onSettled: (_data, _error, _variables, context) => {
      if (context?.toastId) toast.dismiss(context.toastId);
    },
  });

  const isCreateBusy = createMutation.isPending || createAndRunMutation.isPending || createAndOpenMappingMutation.isPending;
  const canSubmit = useMemo(() => Boolean(form.url?.trim()), [form.url]);

  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Sources</h1>
        <Button fullWidth={isMobile} className="sm:w-auto" onClick={() => setShowDialog(true)}>Add Source</Button>
      </div>

      {actionFeedback && <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm">{actionFeedback}</div>}

      {isMobile ? (
        <div className="space-y-3">
          {isLoading && (
            <div className="space-y-3" role="status" aria-label="Loading sources">
              {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-28 rounded-lg border" />)}
            </div>
          )}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <EmptyState
              icon={Sparkles}
              title="No sources yet"
              description="Add your first art website source to start crawling, classifying, and extracting records."
              actionLabel="Add Source"
              onAction={() => setShowDialog(true)}
            />
          )}
          {data?.items.map((source) => (
            <SourceMobileCard key={source.id} source={source} onView={() => navigate(`/sources/${source.id}`)} />
          ))}
        </div>
      ) : (
      <div className="bg-card rounded-lg border overflow-hidden">
        <table className="w-full text-sm block overflow-x-auto lg:table">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left p-3 font-medium text-muted-foreground">Name / URL</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Status</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Pages</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Records</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Last Run</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <SkeletonTableRows columns={6} rows={4} />}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <tr>
                <td colSpan={6} className="p-4">
                  <EmptyState
                    icon={Sparkles}
                    title="No sources connected"
                    description="Create a source and kick off discovery mining to populate this table with crawl progress and results."
                    actionLabel="Add Source"
                    onAction={() => setShowDialog(true)}
                  />
                </td>
              </tr>
            )}
            {data?.items.map((source) => (
              <tr key={source.id} className="border-t hover:bg-muted/40">
                <td className="p-3">
                  <div className="font-medium">{source.name ?? source.url}</div>
                  <div className="text-xs text-muted-foreground truncate max-w-xs">{source.url}</div>
                </td>
                <td className="p-3"><StatusBadge status={source.operational_status ?? source.status} /></td>
                <td className="p-3">{source.total_pages}</td>
                <td className="p-3">{source.total_records}</td>
                <td className="p-3 text-muted-foreground">{source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"}</td>
                <td className="p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <button onClick={() => navigate(`/sources/${source.id}`)} className="p-1 text-muted-foreground hover:text-blue-600" title="View"><Eye size={16} /></button>
                    <button
                      disabled={actionMutation.isPending}
                      onClick={() => actionMutation.mutate({ sourceId: source.id, action: "start-discovery" })}
                      className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    >
                      {actionMutation.isPending ? "Loading..." : "Start Discovery"}
                    </button>
                    <button
                      disabled={actionMutation.isPending}
                      onClick={() => actionMutation.mutate({ sourceId: source.id, action: "start-full" })}
                      className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    >
                      {actionMutation.isPending ? "Loading..." : "Start Full Mining"}
                    </button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "pause" })} className="p-1 text-muted-foreground hover:text-amber-600" title="Pause"><Pause size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "resume" })} className="p-1 text-muted-foreground hover:text-green-600" title="Resume"><Play size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "stop" })} className="p-1 text-muted-foreground hover:text-red-600" title="Stop"><Square size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "retry-failed" })} className="p-1 text-muted-foreground hover:text-indigo-600" title="Retry Failed"><RotateCcw size={16} /></button>
                    <button
                      onClick={() => {
                        if (confirm("Delete this source and all its data?")) deleteMutation.mutate(source.id);
                      }}
                      className="p-1 text-muted-foreground hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}

      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-4 lg:p-6 w-full max-w-2xl shadow-xl mx-4">
            <h2 className="text-lg font-semibold mb-4">Add Source</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div className="sm:col-span-2">
                <label className="block mb-1">URL *</label>
                <Input type="url" value={form.url ?? ""} onChange={(e) => setForm((prev) => ({ ...prev, url: e.target.value }))} className="w-full" />
              </div>
              <div>
                <label className="block mb-1">Name</label>
                <Input value={form.name ?? ""} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} className="w-full" />
              </div>
              <div>
                <label className="block mb-1">Crawl intent</label>
                <Select
                  value={form.crawl_intent ?? "site_root"}
                  onChange={(e) => setForm((prev) => ({ ...prev, crawl_intent: e.target.value as CreateSourceInput["crawl_intent"] }))}
                  className="w-full"
                  options={CRAWL_INTENT_OPTIONS.map((option) => ({ value: String(option.value ?? "site_root"), label: option.label }))}
                />
              </div>
              <div>
                <label className="block mb-1">Max pages</label>
                <Input type="number" min={1} value={form.max_pages ?? ""} onChange={(e) => setForm((prev) => ({ ...prev, max_pages: e.target.value ? Number(e.target.value) : undefined }))} className="w-full" />
              </div>
              <div>
                <label className="block mb-1">Max depth</label>
                <Input type="number" min={1} value={form.max_depth ?? ""} onChange={(e) => setForm((prev) => ({ ...prev, max_depth: e.target.value ? Number(e.target.value) : undefined }))} className="w-full" />
              </div>
              <div className="sm:col-span-2">
                <label className="block mb-1">Crawl hints (JSON)</label>
                <textarea rows={2} placeholder='{"seed": ["/artists"]}' className="w-full border rounded px-3 py-2" onChange={(e) => {
                  try {
                    const value = e.target.value.trim();
                    setForm((prev) => ({ ...prev, crawl_hints: value ? JSON.parse(value) : undefined }));
                    setError(null);
                  } catch {
                    setError("Invalid crawl hints JSON");
                  }
                }} />
              </div>
              <div className="sm:col-span-2">
                <label className="block mb-1">Extraction rules (JSON)</label>
                <textarea rows={2} placeholder='{"artists": {"required": ["title"]}}' className="w-full border rounded px-3 py-2" onChange={(e) => {
                  try {
                    const value = e.target.value.trim();
                    setForm((prev) => ({ ...prev, extraction_rules: value ? JSON.parse(value) : undefined }));
                    setError(null);
                  } catch {
                    setError("Invalid extraction rules JSON");
                  }
                }} />
              </div>
              <label className="sm:col-span-2 flex items-center gap-2">
                <input type="checkbox" checked={form.enabled ?? true} onChange={(e) => setForm((prev) => ({ ...prev, enabled: e.target.checked }))} />
                Enabled
              </label>
            </div>
            <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2 mt-4">
              <Button fullWidth={isMobile} disabled={!canSubmit || isCreateBusy} onClick={() => createMutation.mutate(form)} variant="secondary">Save Source</Button>
              <Button fullWidth={isMobile} disabled={!canSubmit || isCreateBusy} onClick={() => createAndOpenMappingMutation.mutate()} variant="secondary">Save & Open Mapping Scan</Button>
              <Button fullWidth={isMobile} disabled={!canSubmit || isCreateBusy} onClick={() => createAndRunMutation.mutate({ action: "start-discovery" })}>Save & Start Discovery</Button>
              <Button fullWidth={isMobile} disabled={!canSubmit || isCreateBusy} onClick={() => createAndRunMutation.mutate({ action: "start-full" })}>Save & Start Full Mining</Button>
              <Button fullWidth={isMobile} onClick={() => setShowDialog(false)} variant="ghost">Cancel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SourceMobileCard({ source, onView }: { source: Source; onView: () => void }) {
  return (
    <MobileCard>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-foreground truncate">{source.name ?? source.url}</h3>
          <p className="text-xs text-muted-foreground truncate mt-1">{source.url}</p>
        </div>
        <StatusBadge status={source.operational_status ?? source.status} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <MobileCardRow label="Pages" value={source.total_pages} />
        <MobileCardRow label="Records" value={source.total_records} />
        <MobileCardRow label="Last run" value={source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"} />
        <MobileCardRow label="Intent" value={source.crawl_intent ?? "—"} />
      </div>
      <Button fullWidth onClick={onView} variant="secondary">View source</Button>
    </MobileCard>
  );
}
