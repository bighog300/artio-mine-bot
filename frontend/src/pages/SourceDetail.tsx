import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSource, startMining, pauseMining, deleteSource, getPages, getRecords, getMiningStatus } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { formatDate } from "@/lib/utils";

export function SourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "pages" | "records" | "jobs">("overview");
  const [startFeedback, setStartFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const { data: source, isLoading } = useQuery({
    queryKey: ["source", id],
    queryFn: () => getSource(id!),
    enabled: !!id,
  });
  const { data: miningStatus } = useQuery({
    queryKey: ["mine-status", id],
    queryFn: () => getMiningStatus(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return 5000;
      return ["queued", "pending", "running", "mapping", "crawling", "extracting"].includes(status)
        ? 3000
        : 10000;
    },
  });

  const { data: pages } = useQuery({
    queryKey: ["pages", id],
    queryFn: () => getPages({ source_id: id, limit: 50 }),
    enabled: activeTab === "pages" && !!id,
  });

  const { data: records } = useQuery({
    queryKey: ["records", id],
    queryFn: () => getRecords({ source_id: id, limit: 50 }),
    enabled: activeTab === "records" && !!id,
  });

  const startMutation = useMutation({
    mutationFn: () => startMining(id!),
    onSuccess: () => {
      setStartFeedback({ type: "success", message: "Mining queued successfully." });
      queryClient.invalidateQueries({ queryKey: ["source", id] });
      queryClient.invalidateQueries({ queryKey: ["mine-status", id] });
    },
    onError: (e: Error) => {
      setStartFeedback({ type: "error", message: e.message });
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => pauseMining(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["source", id] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSource(id!),
    onSuccess: () => navigate("/sources"),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!source) return <div className="p-6 text-red-500">Source not found</div>;

  const siteMap = source.site_map ? JSON.parse(source.site_map) : null;

  const tabs = ["overview", "pages", "records", "jobs"] as const;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate("/sources")} className="text-sm text-gray-500 hover:text-gray-700 mb-1">
            ← Sources
          </button>
          <h1 className="text-2xl font-bold">{source.name ?? source.url}</h1>
          <p className="text-sm text-gray-500">{source.url}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
            className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {startMutation.isPending ? "Starting..." : "Start Mining"}
          </button>
          <button
            onClick={() => pauseMutation.mutate()}
            className="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50"
          >
            Pause
          </button>
          <button
            onClick={() => { if (confirm("Delete?")) deleteMutation.mutate(); }}
            className="px-3 py-1.5 border border-red-300 text-red-600 rounded text-sm hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      </div>
      {startFeedback && (
        <div
          className={`rounded border px-3 py-2 text-sm ${
            startFeedback.type === "success"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {startFeedback.message}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-1 text-sm font-medium border-b-2 capitalize ${
                activeTab === tab
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Overview */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white border rounded p-4">
              <div className="text-sm text-gray-500">Status</div>
              <div className="mt-1"><StatusBadge status={miningStatus?.status ?? source.status} /></div>
            </div>
            <div className="bg-white border rounded p-4">
              <div className="text-sm text-gray-500">Pages Crawled</div>
              <div className="text-2xl font-bold mt-1">{miningStatus?.progress?.pages_crawled ?? source.total_pages}</div>
            </div>
            <div className="bg-white border rounded p-4">
              <div className="text-sm text-gray-500">Records Extracted</div>
              <div className="text-2xl font-bold mt-1">{miningStatus?.progress?.records_extracted ?? source.total_records}</div>
            </div>
          </div>
          <div className="bg-white border rounded p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-500">Mining Progress</div>
              <div className="text-sm font-medium">{miningStatus?.progress?.percent_complete ?? 0}%</div>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all"
                style={{ width: `${miningStatus?.progress?.percent_complete ?? 0}%` }}
              />
            </div>
            {miningStatus?.current_job && (
              <div className="text-xs text-gray-500">
                Current job: {miningStatus.current_job.job_type} ({miningStatus.current_job.status})
              </div>
            )}
          </div>

          {siteMap && (
            <div className="bg-white border rounded p-4">
              <h3 className="font-medium mb-3">Site Map — {siteMap.platform}</h3>
              <div className="space-y-2">
                {siteMap.sections?.map((section: { name: string; url: string; content_type: string; confidence: number }, i: number) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div>
                      <div className="font-medium text-sm">{section.name}</div>
                      <div className="text-xs text-gray-500">{section.url}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        {section.content_type}
                      </span>
                      <span className="text-xs text-gray-500">{section.confidence}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pages tab */}
      {activeTab === "pages" && (
        <div className="bg-white border rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3 font-medium text-gray-600">URL</th>
                <th className="text-left p-3 font-medium text-gray-600">Type</th>
                <th className="text-left p-3 font-medium text-gray-600">Status</th>
                <th className="text-left p-3 font-medium text-gray-600">Depth</th>
              </tr>
            </thead>
            <tbody>
              {pages?.items.map((page) => (
                <tr key={page.id} className="border-t">
                  <td className="p-3 max-w-xs truncate">{page.url}</td>
                  <td className="p-3 text-xs">{page.page_type}</td>
                  <td className="p-3"><StatusBadge status={page.status} /></td>
                  <td className="p-3">{page.depth}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Records tab */}
      {activeTab === "records" && (
        <div className="grid grid-cols-3 gap-3">
          {records?.items.map((record) => (
            <div key={record.id} className="bg-white border rounded p-3 space-y-2">
              <div className="flex items-center justify-between">
                <RecordTypeBadge type={record.record_type} />
                <ConfidenceBadge band={record.confidence_band as "HIGH" | "MEDIUM" | "LOW"} score={record.confidence_score} />
              </div>
              <div className="font-medium text-sm truncate">{record.title ?? "Untitled"}</div>
              <StatusBadge status={record.status} />
            </div>
          ))}
          {records?.items.length === 0 && (
            <div className="col-span-3 text-center text-gray-400 p-6">No records extracted yet.</div>
          )}
        </div>
      )}

      {/* Jobs tab */}
      {activeTab === "jobs" && (
        <div className="text-gray-400 text-center p-6">Jobs view — run a mining operation to see jobs.</div>
      )}
    </div>
  );
}
