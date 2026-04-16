import { JobEvent } from "@/lib/api";

export function JobEventTimeline({ items }: { items: JobEvent[] }) {
  if (items.length === 0) return <div className="text-sm text-gray-400">No events yet.</div>;
  return (
    <div className="space-y-3">
      {items.map((event) => (
        <div key={event.id} className="border rounded p-3 bg-white">
          <div className="flex gap-2 text-xs text-gray-500">
            <span>{new Date(event.timestamp).toLocaleString()}</span>
            <span className="px-1 rounded bg-gray-100">{event.event_type}</span>
            {event.stage && <span className="px-1 rounded bg-blue-100 text-blue-700">{event.stage}</span>}
          </div>
          <div className="mt-1 text-sm">{event.message}</div>
        </div>
      ))}
    </div>
  );
}
