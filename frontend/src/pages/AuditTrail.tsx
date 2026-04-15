import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAuditActions } from "@/lib/api";
import { formatRelative } from "@/lib/utils";

export function AuditTrail() {
  const [actionType, setActionType] = useState("");
  const { data } = useQuery({
    queryKey: ["audit-actions", actionType],
    queryFn: () => getAuditActions({ action_type: actionType || undefined }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
      <select value={actionType} onChange={(e) => setActionType(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
        <option value="">All actions</option>
        <option value="conflict_resolution">Conflict resolutions</option>
        <option value="merge">Merges</option>
        <option value="rerun">Reruns</option>
        <option value="record_update">Record edits</option>
      </select>

      <div className="bg-white border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-3 text-left">Action</th>
              <th className="p-3 text-left">User</th>
              <th className="p-3 text-left">Affected records</th>
              <th className="p-3 text-left">Time</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((action) => (
              <tr key={action.id} className="border-t">
                <td className="p-3">{action.action_type}</td>
                <td className="p-3">{action.user ?? "system"}</td>
                <td className="p-3">{action.affected_records.join(", ") || "—"}</td>
                <td className="p-3">{formatRelative(action.timestamp)}</td>
              </tr>
            ))}
            {(data?.items.length ?? 0) === 0 && <tr><td colSpan={4} className="p-4 text-gray-500">No audit actions yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
