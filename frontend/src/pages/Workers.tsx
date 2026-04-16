import { useQuery } from "@tanstack/react-query";

import { Badge, Spinner } from "@/components/ui";
import { getWorkers } from "@/lib/api";

export function Workers() {
  const { data, isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: getWorkers,
    refetchInterval: 3000,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Workers</h1>
      <div className="bg-white border rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3">Worker</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Current job</th>
              <th className="text-left p-3">Stage</th>
              <th className="text-left p-3">Heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="p-6">
                  <div className="flex justify-center">
                    <Spinner label="Loading workers" />
                  </div>
                </td>
              </tr>
            )}
            {(data?.items ?? []).map((worker) => (
              <tr key={worker.worker_id} className="border-t">
                <td className="p-3 font-mono text-xs">{worker.worker_id}</td>
                <td className="p-3">
                  <Badge variant={worker.status === "running" ? "success" : "default"}>{worker.status}</Badge>
                </td>
                <td className="p-3 text-xs">{worker.current_job_id ?? "—"}</td>
                <td className="p-3 text-xs">{worker.stage ?? "—"}</td>
                <td className="p-3 text-xs">{worker.heartbeat ? new Date(worker.heartbeat).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
