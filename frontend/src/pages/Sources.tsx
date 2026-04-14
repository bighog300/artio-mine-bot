import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Plus, Play, Trash2, Eye } from "lucide-react";
import { getSources, createSource, deleteSource, startMining } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatRelative } from "@/lib/utils";

export function Sources() {
  const [showDialog, setShowDialog] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [startFeedback, setStartFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({ queryKey: ["sources"], queryFn: getSources });

  const createMutation = useMutation({
    mutationFn: async () => {
      const source = await createSource({ url: urlInput, name: nameInput || undefined });
      await startMining(source.id);
      return source;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      setShowDialog(false);
      setUrlInput("");
      setNameInput("");
    },
    onError: (e: Error) => setError(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources"] }),
  });

  const startMutation = useMutation({
    mutationFn: (sourceId: string) => startMining(sourceId),
    onSuccess: () => {
      setStartFeedback({ type: "success", message: "Mining queued successfully." });
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
    onError: (e: Error) => setStartFeedback({ type: "error", message: e.message }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={16} /> Add Source
        </button>
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

      {/* Table */}
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
                <td className="p-3"><StatusBadge status={source.status} /></td>
                <td className="p-3">{source.total_pages}</td>
                <td className="p-3">{source.total_records}</td>
                <td className="p-3 text-gray-500">
                  {source.last_crawled_at ? formatRelative(source.last_crawled_at) : "Never"}
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/sources/${source.id}`)}
                      className="p-1 text-gray-500 hover:text-blue-600"
                      title="View"
                    >
                      <Eye size={16} />
                    </button>
                    <button
                      onClick={() => startMutation.mutate(source.id)}
                      disabled={startMutation.isPending}
                      className="p-1 text-gray-500 hover:text-green-600 disabled:opacity-50"
                      title="Run"
                    >
                      <Play size={16} />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm("Delete this source and all its data?")) {
                          deleteMutation.mutate(source.id);
                        }
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
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="p-6 text-center text-gray-400">
                  No sources yet. Click "Add Source" to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add Source Dialog */}
      {showDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-semibold mb-4">Add Source</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL *</label>
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example-gallery.com"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name (optional)</label>
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="Gallery Name"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!urlInput || createMutation.isPending}
                className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
              >
                {createMutation.isPending ? "Starting..." : "Add & Start Mining"}
              </button>
              <button
                onClick={() => { setShowDialog(false); setError(null); }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
