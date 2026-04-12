import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getExportPreview, pushToArtio, getSources } from "@/lib/api";

export function Export() {
  const [sourceId, setSourceId] = useState("");
  const [result, setResult] = useState<{ exported_count: number; failed_count: number; errors: string[] } | null>(null);

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data: preview } = useQuery({
    queryKey: ["export-preview", sourceId],
    queryFn: () => getExportPreview(sourceId || undefined),
  });

  const pushMutation = useMutation({
    mutationFn: () => pushToArtio({ source_id: sourceId || undefined }),
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Export to Artio</h1>

      {/* Connection status */}
      <div className={`p-4 rounded-lg border ${preview?.artio_configured ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200"}`}>
        <div className="text-sm font-medium">
          {preview?.artio_configured ? "Artio API configured" : "Artio API not configured"}
        </div>
        {!preview?.artio_configured && (
          <div className="text-xs text-yellow-700 mt-1">
            Set ARTIO_API_URL and ARTIO_API_KEY in your .env file to enable export.
          </div>
        )}
      </div>

      {/* Preview */}
      <div className="bg-white border rounded-lg p-4 space-y-4">
        <h2 className="font-semibold text-gray-900">Export Preview</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 rounded p-3">
            <div className="text-sm text-gray-500">Ready to export</div>
            <div className="text-3xl font-bold text-blue-600">{preview?.record_count ?? 0}</div>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <div className="text-sm text-gray-500">By type</div>
            <div className="space-y-1 mt-1">
              {Object.entries(preview?.by_type ?? {}).map(([type, count]) => (
                count > 0 && (
                  <div key={type} className="flex justify-between text-sm">
                    <span className="capitalize text-gray-600">{type}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Source (optional)</label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">All sources</option>
              {sources?.items.map((s) => (
                <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => pushMutation.mutate()}
            disabled={pushMutation.isPending || !preview?.artio_configured}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
          >
            {pushMutation.isPending ? "Pushing..." : "Push to Artio"}
          </button>
        </div>

        {result && (
          <div className={`p-3 rounded border text-sm ${result.failed_count > 0 ? "bg-yellow-50 border-yellow-200" : "bg-green-50 border-green-200"}`}>
            <div className="font-medium">
              Exported {result.exported_count} records.
              {result.failed_count > 0 && ` ${result.failed_count} failed.`}
            </div>
            {result.errors.length > 0 && (
              <ul className="mt-2 text-xs text-red-600 space-y-1">
                {result.errors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
