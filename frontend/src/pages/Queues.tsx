import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getQueues, pauseQueue, resumeQueue } from "@/lib/api";

export function Queues() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["queues"], queryFn: getQueues, refetchInterval: 5000 });
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
          </div>
        ))}
      </div>
    </div>
  );
}
