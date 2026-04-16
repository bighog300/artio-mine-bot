import { useQuery } from "@tanstack/react-query";
import { getPages, getSources } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useState } from "react";
import { Select } from "@/components/ui";

export function Pages() {
  const [sourceId, setSourceId] = useState("");
  const [status, setStatus] = useState("");
  const [pageType, setPageType] = useState("");

  const { data: sources } = useQuery({ queryKey: ["sources"], queryFn: getSources });
  const { data, isLoading } = useQuery({
    queryKey: ["pages", { sourceId, status, pageType }],
    queryFn: () => getPages({
      source_id: sourceId || undefined,
      status: status || undefined,
      page_type: pageType || undefined,
    }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Pages</h1>

      <div className="flex gap-3 flex-wrap">
        <select
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All sources</option>
          {sources?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          {["pending", "fetched", "classified", "extracted", "error", "skipped"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3 font-medium text-gray-600">URL</th>
              <th className="text-left p-3 font-medium text-gray-600">Type</th>
              <th className="text-left p-3 font-medium text-gray-600">Status</th>
              <th className="text-left p-3 font-medium text-gray-600">Depth</th>
              <th className="text-left p-3 font-medium text-gray-600">Method</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={5} className="p-6 text-center text-gray-400">Loading...</td></tr>
            )}
            {data?.items.map((page) => (
              <tr key={page.id} className="border-t hover:bg-gray-50">
                <td className="p-3 max-w-sm">
                  <div className="truncate">{page.url}</div>
                  {page.title && <div className="text-xs text-gray-500 truncate">{page.title}</div>}
                </td>
                <td className="p-3 text-xs">{page.page_type}</td>
                <td className="p-3"><StatusBadge status={page.status} /></td>
                <td className="p-3">{page.depth}</td>
                <td className="p-3 text-xs text-gray-500">{page.fetch_method ?? "—"}</td>
              </tr>
            ))}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-400">No pages found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
