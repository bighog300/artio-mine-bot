import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  deleteSource,
  getMiningStatus,
  getPages,
  getRecords,
  getSource,
  getSourceJobs,
  mapSite,
  pauseSource,
  resumeSource,
  retryFailedSource,
  startMining,
  stopSource,
  updateSource,
} from "@/lib/api";
import { MiningProgress } from "@/components/shared/MiningProgress";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Button, Checkbox, Input, Select } from "@/components/ui";

export function SourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "pages" | "records" | "jobs" | "settings" | "mapping">("overview");
  const [message, setMessage] = useState<string | null>(null);

  const { data: source, isLoading } = useQuery({ queryKey: ["source", id], queryFn: () => getSource(id!), enabled: !!id });
  const { data: miningStatus } = useQuery({
    queryKey: ["mine-status", id],
    queryFn: () => getMiningStatus(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const current = query.state.data;
      const currentStatus = current?.status;
      if (!currentStatus) return 3000;
      return ["done", "error", "paused", "stopped"].includes(currentStatus) ? false : 3000;
    },
  });
  const { data: pages } = useQuery({ queryKey: ["pages", id], queryFn: () => getPages({ source_id: id, limit: 50 }), enabled: activeTab === "pages" && !!id });
  const { data: records } = useQuery({ queryKey: ["records", id], queryFn: () => getRecords({ source_id: id, limit: 50 }), enabled: activeTab === "records" && !!id });
  const { data: jobs } = useQuery({ queryKey: ["source-jobs", id], queryFn: () => getSourceJobs(id!), enabled: !!id, refetchInterval: 5000 });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["source", id] });
    queryClient.invalidateQueries({ queryKey: ["sources"] });
    queryClient.invalidateQueries({ queryKey: ["mine-status", id] });
    queryClient.invalidateQueries({ queryKey: ["source-jobs", id] });
  };

  const actionMutation = useMutation({
    mutationFn: async (action: "discovery" | "full" | "pause" | "resume" | "stop" | "retry") => {
      if (!id) return;
      if (action === "discovery") return mapSite(id);
      if (action === "full") return startMining(id);
      if (action === "pause") return pauseSource(id);
      if (action === "resume") return resumeSource(id);
      if (action === "stop") return stopSource(id);
      return retryFailedSource(id);
    },
    onSuccess: () => {
      setMessage("Action queued.");
      refresh();
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const updateSettingsMutation = useMutation({
    mutationFn: () =>
      updateSource(id!, {
        crawl_intent:
          source?.crawl_intent === "directory_listing" ||
          source?.crawl_intent === "detail_entity" ||
          source?.crawl_intent === "test_crawl" ||
          source?.crawl_intent === "site_root"
            ? source.crawl_intent
            : "site_root",
        max_depth: source?.max_depth ?? undefined,
        max_pages: source?.max_pages ?? undefined,
        enabled: source?.enabled,
        crawl_hints: source?.crawl_hints ?? undefined,
        extraction_rules: source?.extraction_rules ?? undefined,
      }),
    onSuccess: () => {
      setMessage("Settings saved.");
      refresh();
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSource(id!),
    onSuccess: () => navigate("/sources"),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!source) return <div className="p-6 text-red-500">Source not found</div>;

  const tabs = ["overview", "pages", "records", "jobs", "mapping", "settings"] as const;

  return (
    <div className="space-y-4">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate("/sources")} className="mb-1">← Sources</Button>
        <h1 className="text-2xl font-bold">{source.name ?? source.url}</h1>
        <p className="text-sm text-gray-500">{source.url}</p>
      </div>

      {message && <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm">{message}</div>}

      <div className="bg-white border rounded p-4">
        <h2 className="font-semibold mb-3">Operational Controls</h2>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <StatusBadge status={source.operational_status ?? source.status} />
          <Button size="sm" variant="secondary" onClick={() => navigate(`/sources/${id}/operations`)}>Open Operations Console</Button>
          <Button size="sm" variant="primary" onClick={() => actionMutation.mutate("discovery")}>Start Discovery</Button>
          <Button size="sm" variant="primary" onClick={() => actionMutation.mutate("full")}>Start Full Mining</Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("pause")}>Pause</Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("resume")}>Resume</Button>
          <Button size="sm" variant="danger" onClick={() => actionMutation.mutate("stop")}>Stop</Button>
          <Button size="sm" variant="secondary" onClick={() => actionMutation.mutate("retry")}>Retry Failed</Button>
          <Button size="sm" variant="danger" onClick={() => { if (confirm("Delete this source and all data?")) deleteMutation.mutate(); }}>Delete</Button>
        </div>
        <div className="mt-3">
          <MiningProgress
            status={miningStatus?.status ?? source.status}
            progress={miningStatus?.progress}
            errorMessage={source.error_message}
            onRetry={() => actionMutation.mutate("full")}
            retryPending={actionMutation.isPending}
          />
        </div>
      </div>

      <div className="border-b">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)} className={`py-2 px-1 text-sm font-medium border-b-2 capitalize ${activeTab === tab ? "border-blue-500 text-blue-600" : "border-transparent text-gray-500"}`}>
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "overview" && <div className="bg-white border rounded p-4 text-sm text-gray-700">Source created at {new Date(source.created_at).toLocaleString()} with current status <strong>{source.operational_status ?? source.status}</strong>.</div>}

      {activeTab === "pages" && (
        <div className="bg-white border rounded overflow-hidden">
          <table className="w-full text-sm"><thead className="bg-gray-50"><tr><th className="text-left p-3">URL</th><th className="text-left p-3">Type</th><th className="text-left p-3">Status</th></tr></thead>
            <tbody>{pages?.items.map((p) => <tr key={p.id} className="border-t"><td className="p-3 truncate max-w-[440px]">{p.url}</td><td className="p-3">{p.page_type}</td><td className="p-3"><StatusBadge status={p.status} /></td></tr>)}</tbody>
          </table>
        </div>
      )}

      {activeTab === "records" && (
        <div className="bg-white border rounded p-4 text-sm">{records?.items.length ?? 0} records found.</div>
      )}

      {activeTab === "mapping" && (
        <div className="bg-white border rounded p-4 text-sm space-y-3">
          <p>Configure AI Source Mapper scans, mappings, and preview output for this source.</p>
          <Button className="w-fit" onClick={() => navigate(`/sources/${id}/mapping`)}>
            Open Mapping Workspace
          </Button>
        </div>
      )}

      {activeTab === "jobs" && (
        <div className="bg-white border rounded overflow-hidden">
          <table className="w-full text-sm"><thead className="bg-gray-50"><tr><th className="text-left p-3">Type</th><th className="text-left p-3">Status</th><th className="text-left p-3">Started</th><th className="text-left p-3">Completed</th></tr></thead>
            <tbody>{(jobs?.items ?? []).map((job) => <tr key={job.id} className="border-t"><td className="p-3">{job.job_type}</td><td className="p-3"><StatusBadge status={job.status} /></td><td className="p-3">{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</td><td className="p-3">{job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}</td></tr>)}</tbody>
          </table>
        </div>
      )}

      {activeTab === "settings" && (
        <div className="bg-white border rounded p-4 space-y-3 text-sm">
          <h3 className="font-semibold">Source behavior settings</h3>
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-1">
              <span className="text-gray-600">Crawl intent</span>
              <Select
                className="w-full"
                value={source.crawl_intent ?? "site_root"}
                onChange={(e) => queryClient.setQueryData(["source", id], { ...source, crawl_intent: e.target.value })}
                options={[
                  { value: "site_root", label: "Site root" },
                  { value: "directory_listing", label: "Directory/listing page" },
                  { value: "detail_entity", label: "Detail/entity page" },
                  { value: "test_crawl", label: "Test crawl" },
                ]}
              />
            </label>
            <label className="space-y-1">
              <span className="text-gray-600">Max pages</span>
              <Input type="number" className="w-full" value={source.max_pages ?? ""} onChange={(e) => queryClient.setQueryData(["source", id], { ...source, max_pages: e.target.value ? Number(e.target.value) : undefined })} />
            </label>
            <label className="space-y-1">
              <span className="text-gray-600">Max depth</span>
              <Input type="number" className="w-full" value={source.max_depth ?? ""} onChange={(e) => queryClient.setQueryData(["source", id], { ...source, max_depth: e.target.value ? Number(e.target.value) : undefined })} />
            </label>
            <label className="flex items-center gap-2 mt-6">
              <Checkbox id="source-enabled" checked={source.enabled ?? true} onChange={(checked) => queryClient.setQueryData(["source", id], { ...source, enabled: checked })} label="" />
              Enabled
            </label>
          </div>
          <Button onClick={() => updateSettingsMutation.mutate()}>Save Settings</Button>
        </div>
      )}
    </div>
  );
}
