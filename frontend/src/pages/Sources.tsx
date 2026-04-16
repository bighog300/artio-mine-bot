import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Eye, Pause, Play, RotateCcw, Square, Trash2 } from "lucide-react";
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
import { formatRelative } from "@/lib/utils";
import { Button, Input, Select } from "@/components/ui";

type SourceAction = "start-discovery" | "start-full" | "pause" | "resume" | "stop" | "retry-failed";

const CRAWL_INTENT_OPTIONS: Array<{ value: CreateSourceInput["crawl_intent"]; label: string }> = [
  { value: "site_root", label: "Site root" },
  { value: "directory_listing", label: "Directory/listing page" },
  { value: "detail_entity", label: "Detail/entity page" },
  { value: "test_crawl", label: "Test crawl" },
];

export function Sources() {
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

  const { data, isLoading } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const createMutation = useMutation({
    mutationFn: createSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
    },
    onError: (e: Error) => setError(e.message),
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setActionFeedback("Source saved and job started.");
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
    },
    onError: (e: Error) => setError(e.message),
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
    onSuccess: ({ sourceId, draftId }) => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setError(null);
      setActionFeedback("Source saved and mapping scan started.");
      setForm({ url: "", name: "", crawl_intent: "site_root", enabled: true });
      navigate(`/sources/${sourceId}/mapping?draft=${draftId}`);
    },
    onError: (e: Error) => setError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });

  const actionMutation = useMutation({
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
    onSuccess: () => {
      setActionFeedback("Source action accepted.");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
    onError: (e: Error) => setActionFeedback(e.message),
  });

  const isCreateBusy = createMutation.isPending || createAndRunMutation.isPending || createAndOpenMappingMutation.isPending;
  const canSubmit = useMemo(() => Boolean(form.url?.trim()), [form.url]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
        <Button onClick={() => setShowDialog(true)}>Add Source</Button>
      </div>

      {actionFeedback && <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm">{actionFeedback}</div>}

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3 font-medium text-gray-600">Name / URL</th>
              <th className="text-left p-3 font-medium text-gray-600">Status</th>
              <th className="text-left p-3 font-medium text-gray-600">Pages</th>
              <th className="text-left p-3 font-medium text-gray-600">Records</th>
              <th className="text-left p-3 font-medium text-gray-600">Last Run</th>
              <th className="text-left p-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={6} className="p-6 text-center text-gray-400">Loading...</td></tr>
            )}
            {data?.items.map((source) => (
              <tr key={source.id} className="border-t hover:bg-gray-50">
                <td className="p-3">
                  <div className="font-medium">{source.name ?? source.url}</div>
                  <div className="text-xs text-gray-500 truncate max-w-xs">{source.url}</div>
                </td>
                <td className="p-3"><StatusBadge status={source.operational_status ?? source.status} /></td>
                <td className="p-3">{source.total_pages}</td>
                <td className="p-3">{source.total_records}</td>
                <td className="p-3 text-gray-500">{source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"}</td>
                <td className="p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <button onClick={() => navigate(`/sources/${source.id}`)} className="p-1 text-gray-500 hover:text-blue-600" title="View"><Eye size={16} /></button>
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
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "pause" })} className="p-1 text-gray-500 hover:text-amber-600" title="Pause"><Pause size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "resume" })} className="p-1 text-gray-500 hover:text-green-600" title="Resume"><Play size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "stop" })} className="p-1 text-gray-500 hover:text-red-600" title="Stop"><Square size={16} /></button>
                    <button onClick={() => actionMutation.mutate({ sourceId: source.id, action: "retry-failed" })} className="p-1 text-gray-500 hover:text-indigo-600" title="Retry Failed"><RotateCcw size={16} /></button>
                    <button
                      onClick={() => {
                        if (confirm("Delete this source and all its data?")) deleteMutation.mutate(source.id);
                      }}
                      className="p-1 text-gray-500 hover:text-red-600"
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

      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Add Source</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="col-span-2">
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
              <div className="col-span-2">
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
              <div className="col-span-2">
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
              <label className="col-span-2 flex items-center gap-2">
                <input type="checkbox" checked={form.enabled ?? true} onChange={(e) => setForm((prev) => ({ ...prev, enabled: e.target.checked }))} />
                Enabled
              </label>
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              <Button disabled={!canSubmit || isCreateBusy} onClick={() => createMutation.mutate(form)} variant="secondary">Save Source</Button>
              <Button disabled={!canSubmit || isCreateBusy} onClick={() => createAndOpenMappingMutation.mutate()} variant="secondary">Save & Open Mapping Scan</Button>
              <Button disabled={!canSubmit || isCreateBusy} onClick={() => createAndRunMutation.mutate({ action: "start-discovery" })}>Save & Start Discovery</Button>
              <Button disabled={!canSubmit || isCreateBusy} onClick={() => createAndRunMutation.mutate({ action: "start-full" })}>Save & Start Full Mining</Button>
              <Button onClick={() => setShowDialog(false)} variant="ghost">Cancel</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
