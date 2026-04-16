import { JobEvent } from "@/lib/api";

export function JobEventTimeline({ items }: { items: JobEvent[] }) {
  if (items.length === 0) return <div className="text-sm text-muted-foreground/80">No events yet.</div>;
  return (
    <div className="space-y-3">
      {items.map((event) => (
        <div key={event.id} className="border rounded p-3 bg-card">
          <div className="flex gap-2 text-xs text-muted-foreground">
            <span>{new Date(event.timestamp).toLocaleString()}</span>
            <span className="px-1 rounded bg-muted">{event.event_type}</span>
            {event.stage && <span className="px-1 rounded bg-blue-100 text-blue-700">{event.stage}</span>}
          </div>
          <div className="mt-1 text-sm">{event.message}</div>
        </div>
      ))}
    </div>
  );
}
