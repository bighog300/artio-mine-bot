import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createApiKey, deleteApiKey, getApiKeys, getApiUsage } from "@/lib/api";
import { Badge, Button, Input } from "@/components/ui";

export function ApiAccess() {
  const [name, setName] = useState("");
  const [tenantId, setTenantId] = useState("public");
  const [latestKey, setLatestKey] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const keysQuery = useQuery({ queryKey: ["api-keys", tenantId], queryFn: () => getApiKeys(tenantId) });
  const usageQuery = useQuery({ queryKey: ["api-usage", tenantId], queryFn: () => getApiUsage(tenantId) });

  const createMutation = useMutation({
    mutationFn: () => createApiKey({ name, tenant_id: tenantId, permissions: ["read"] }),
    onSuccess: (data) => {
      setLatestKey(data.raw_key);
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["api-keys", tenantId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId, tenantId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["api-keys", tenantId] }),
  });

  const endpointRows = useMemo(() => usageQuery.data?.endpoint_usage ?? [], [usageQuery.data]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">API Access</h1>

      <div className="bg-white border rounded-lg p-4 space-y-3">
        <h2 className="font-semibold">Create API key</h2>
        <div className="grid grid-cols-3 gap-3">
          <Input placeholder="Key name" value={name} onChange={(e) => setName(e.target.value)} />
          <input
            className="border rounded px-3 py-2"
            placeholder="Tenant ID"
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value || "public")}
          />
          <button
            className="bg-blue-600 text-white rounded px-3 py-2 disabled:opacity-60"
            disabled={!name || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? "Creating..." : "Create key"}
          </button>
        </div>
        {latestKey && (
          <p className="text-sm text-green-700">
            Save this key now (shown once): <code>{latestKey}</code>
          </p>
        )}
      </div>

      <div className="bg-white border rounded-lg p-4">
        <h2 className="font-semibold mb-3">API Keys</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-600 border-b">
              <th className="py-2">Name</th>
              <th>Tenant</th>
              <th>Prefix</th>
              <th>Usage</th>
              <th>Last Used</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(keysQuery.data?.items ?? []).map((key) => (
              <tr key={key.id} className="border-b">
                <td className="py-2">{key.name}</td>
                <td>{key.tenant_id}</td>
                <td><code>{key.key_prefix}</code></td>
                <td>{key.usage_count}</td>
                <td>{key.last_used_at ?? "Never"}</td>
                <td>
                  <button
                    className="text-red-600 hover:underline"
                    onClick={() => deleteMutation.mutate(key.id)}
                  >
                    Disable
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white border rounded-lg p-4">
        <h2 className="font-semibold mb-3">Usage Dashboard</h2>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="border rounded p-3">
            <div className="text-xs text-gray-500">Total requests</div>
            <div className="text-xl font-semibold">{usageQuery.data?.total_requests ?? 0}</div>
          </div>
          <div className="border rounded p-3">
            <div className="text-xs text-gray-500">Avg response ms</div>
            <div className="text-xl font-semibold">{Math.round(usageQuery.data?.avg_response_time_ms ?? 0)}</div>
          </div>
        </div>

        <div className="space-y-2">
          {endpointRows.map((item) => (
            <div key={item.endpoint} className="flex items-center justify-between text-sm border rounded px-3 py-2">
              <span>{item.endpoint}</span>
              <span className="font-medium">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
