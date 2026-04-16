import type { AuditEvent } from "@/lib/api";
import { formatRelative } from "@/lib/utils";

interface AuditTimelineProps {
  events: AuditEvent[];
  onSelectEvent: (event: AuditEvent) => void;
}

function groupByDate(events: AuditEvent[]): Array<{ date: string; items: AuditEvent[] }> {
  const map = new Map<string, AuditEvent[]>();
  events.forEach((event) => {
    const date = new Date(event.timestamp).toISOString().slice(0, 10);
    map.set(date, [...(map.get(date) ?? []), event]);
  });
  return Array.from(map.entries()).map(([date, items]) => ({ date, items }));
}

export function AuditTimeline({ events, onSelectEvent }: AuditTimelineProps) {
  const grouped = groupByDate(events);

  if (events.length === 0) {
    return <div className="rounded-lg border bg-white p-8 text-center text-sm text-gray-500">No audit events found for the current filters.</div>;
  }

  return (
    <div className="space-y-6">
      {grouped.map((group) => (
        <section key={group.date}>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-600">{group.date}</h2>
          <div className="space-y-2">
            {group.items.map((event) => (
              <button
                key={event.id}
                type="button"
                onClick={() => onSelectEvent(event)}
                className="w-full rounded-lg border bg-white p-4 text-left hover:border-slate-400"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-gray-900">{event.message || `${event.event_type} ${event.entity_type}`}</p>
                    <p className="text-xs text-gray-500">{event.entity_type}:{event.entity_id} · user: {event.user_name || event.user_id || "system"}</p>
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <p className="uppercase">{event.event_type}</p>
                    <p>{formatRelative(event.timestamp)}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
