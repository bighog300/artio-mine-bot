import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobs, getQueues, pauseQueue, resumeQueue } from "@/lib/api";

export function Queues() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["queues"], queryFn: getQueues, refetchInterval: 5000 });
  const { data: jobs } = useQuery({ queryKey: ["jobs", "queue-view"], queryFn: () => getJobs({ limit: 300 }), refetchInterval: 5000 });
  const queueMutation = useMutation({
    mutationFn: async ({ name, action }: { name: string; action: "pause" | "resume" }) =>
      action === "pause" ? pauseQueue(name) : resumeQueue(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queues"] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Queues</h1>
      <div className="grid gap-3">
        {data?.items.map((queue) => (
          <div key={queue.name} className="bg-white border rounded p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">{queue.name}</h2>
              <div className="flex gap-2 text-sm">
                <button className="px-2 py-1 border rounded" onClick={() => queueMutation.mutate({ name: queue.name, action: "pause" })}>Pause</button>
                <button className="px-2 py-1 border rounded" onClick={() => queueMutation.mutate({ name: queue.name, action: "resume" })}>Resume</button>
              </div>
            </div>
            <div className="grid grid-cols-5 gap-2 text-sm">
              <div><div className="text-gray-500">Pending</div><div className="font-semibold">{queue.pending}</div></div>
              <div><div className="text-gray-500">Running</div><div className="font-semibold">{queue.running}</div></div>
              <div><div className="text-gray-500">Failed</div><div className="font-semibold">{queue.failed}</div></div>
              <div><div className="text-gray-500">Paused</div><div className="font-semibold">{queue.paused}</div></div>
              <div><div className="text-gray-500">Oldest item age</div><div className="font-semibold">{queue.oldest_item_age_seconds}s</div></div>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 text-sm border-t pt-3">
              <div>
                <div className="text-gray-500">Stale jobs</div>
                <div className="font-semibold">{jobs?.items.filter((j) => j.is_stale).length ?? 0}</div>
              </div>
              <div>
                <div className="text-gray-500">Longest running</div>
                <div className="font-semibold">
                  {Math.max(...(jobs?.items.filter((j) => j.status === "running").map((j) => j.duration_seconds ?? 0) ?? [0]))}s
                </div>
              </div>
              <div>
                <div className="text-gray-500">Top stage</div>
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
