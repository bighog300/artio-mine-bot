import { useQuery } from "@tanstack/react-query";

import { Badge, Spinner } from "@/components/ui";
import { MobileCard, MobileCardRow } from "@/components/ui/MobileCard";
import { getWorkers } from "@/lib/api";
import { useIsMobile } from "@/lib/mobile-utils";

export function Workers() {
  const isMobile = useIsMobile();
  const { data, isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: getWorkers,
    refetchInterval: 3000,
  });

  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold">Workers</h1>
      {isMobile ? (
        <div className="space-y-3">
          {(data?.items ?? []).map((worker) => (
            <MobileCard key={worker.worker_id}>
              <div className="flex items-center justify-between gap-2">
                <div className="font-mono text-xs truncate">{worker.worker_id}</div>
                <Badge variant={worker.status === "running" ? "success" : "default"}>{worker.status}</Badge>
              </div>
              <div className="grid grid-cols-1 gap-2">
                <MobileCardRow label="Current job" value={worker.current_job_id ?? "—"} />
                <MobileCardRow label="Stage" value={worker.stage ?? "—"} />
                <MobileCardRow label="Heartbeat" value={worker.heartbeat ? new Date(worker.heartbeat).toLocaleString() : "—"} />
              </div>
            </MobileCard>
          ))}
        </div>
      ) : (
      <div className="bg-card border rounded overflow-hidden">
        <table className="w-full text-sm block overflow-x-auto lg:table">
          <thead className="bg-muted/40">
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
      )}
    </div>
  );
}
