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
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Pages</h1>

      <div className="flex gap-3 flex-wrap">
        <select
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          className="border border-border rounded px-2 py-1.5 text-sm"
        >
          <option value="">All sources</option>
          {sources?.items.map((s) => (
            <option key={s.id} value={s.id}>{s.name ?? s.url}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="border border-border rounded px-2 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          {["pending", "fetched", "classified", "extracted", "error", "skipped"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="bg-card border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left p-3 font-medium text-muted-foreground">URL</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Type</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Status</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Depth</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Method</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={5} className="p-6 text-center text-muted-foreground/80">Loading...</td></tr>
            )}
            {data?.items.map((page) => (
              <tr key={page.id} className="border-t hover:bg-muted/40">
                <td className="p-3 max-w-sm">
                  <div className="truncate">{page.url}</div>
                  {page.title && <div className="text-xs text-muted-foreground truncate">{page.title}</div>}
                </td>
                <td className="p-3 text-xs">{page.page_type}</td>
                <td className="p-3"><StatusBadge status={page.status} /></td>
                <td className="p-3">{page.depth}</td>
                <td className="p-3 text-xs text-muted-foreground">{page.fetch_method ?? "—"}</td>
              </tr>
            ))}
            {!isLoading && data?.items.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-muted-foreground/80">No pages found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
