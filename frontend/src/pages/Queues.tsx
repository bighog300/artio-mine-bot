import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobs, getQueues, getWorkers, pauseQueue, resumeQueue } from "@/lib/api";
import { Badge, Button } from "@/components/ui";
import { useIsMobile } from "@/lib/mobile-utils";

export function Queues() {
  const isMobile = useIsMobile();
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["queues"], queryFn: getQueues, refetchInterval: 5000 });
  const { data: jobs } = useQuery({ queryKey: ["jobs", "queue-view"], queryFn: () => getJobs({ limit: 300 }), refetchInterval: 5000 });
  const { data: workers } = useQuery({ queryKey: ["workers", "queue-view"], queryFn: getWorkers, refetchInterval: 5000 });
  const queueMutation = useMutation({
    mutationFn: async ({ name, action }: { name: string; action: "pause" | "resume" }) =>
      action === "pause" ? pauseQueue(name) : resumeQueue(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queues"] }),
  });

  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold">Queues</h1>
      <div className="grid gap-3">
        {data?.items.map((queue) => (
          <div key={queue.name} className="bg-card border rounded p-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
              <div className="flex items-center gap-2"><h2 className="font-semibold">{queue.name}</h2><Badge variant={queue.paused > 0 ? "warning" : "success"}>{queue.paused > 0 ? "Paused" : "Active"}</Badge></div>
              <div className="grid grid-cols-2 gap-2 text-sm w-full sm:w-auto">
                <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => queueMutation.mutate({ name: queue.name, action: "pause" })}>Pause</Button>
                <Button fullWidth={isMobile} size="sm" variant="secondary" onClick={() => queueMutation.mutate({ name: queue.name, action: "resume" })}>Resume</Button>
              </div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 text-sm">
              <div><div className="text-muted-foreground">Pending</div><div className="font-semibold">{queue.pending}</div></div>
              <div><div className="text-muted-foreground">Running</div><div className="font-semibold">{queue.running}</div></div>
              <div><div className="text-muted-foreground">Failed</div><div className="font-semibold">{queue.failed}</div></div>
              <div><div className="text-muted-foreground">Paused</div><div className="font-semibold">{queue.paused}</div></div>
              <div><div className="text-muted-foreground">Oldest item age</div><div className="font-semibold">{queue.oldest_item_age_seconds}s</div></div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mt-3 text-sm border-t pt-3">
              <div>
                <div className="text-muted-foreground">Active workers</div>
                <div className="font-semibold">{workers?.items.filter((w) => w.status === "running").length ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Stale jobs</div>
                <div className="font-semibold">{jobs?.items.filter((j) => j.is_stale).length ?? 0}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Longest running</div>
                <div className="font-semibold">
                  {Math.max(...(jobs?.items.filter((j) => j.status === "running").map((j) => j.duration_seconds ?? 0) ?? [0]))}s
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Top stage</div>
                <div className="font-semibold">
                  {(() => {
                    const counts = new Map<string, number>();
                    (jobs?.items ?? []).forEach((job) => {
                      if (!job.current_stage || job.status !== "running") return;
                      counts.set(job.current_stage, (counts.get(job.current_stage) ?? 0) + 1);
                    });
                    let top = "—";
                    let max = 0;
                    counts.forEach((count, stage) => {
                      if (count > max) {
                        max = count;
                        top = stage;
                      }
                    });
                    return top;
                  })()}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
