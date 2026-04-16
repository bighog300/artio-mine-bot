import type { AuditEvent } from "@/lib/api";

interface AuditEventModalProps {
  event: AuditEvent;
  onClose: () => void;
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="max-h-64 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}

export function AuditEventModal({ event, onClose }: AuditEventModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-5 shadow-lg">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Audit Event</h2>
            <p className="text-sm text-gray-600">{event.event_type} · {event.entity_type}:{event.entity_id}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded border px-3 py-1.5 text-sm">Close</button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded border p-3 text-sm">
            <p><span className="font-medium">Time:</span> {new Date(event.timestamp).toLocaleString()}</p>
            <p><span className="font-medium">User:</span> {event.user_name || event.user_id || "system"}</p>
            <p><span className="font-medium">Source:</span> {event.source_id || "—"}</p>
            <p><span className="font-medium">Record:</span> {event.record_id || "—"}</p>
          </div>
          <div className="rounded border p-3 text-sm">
            <p className="font-medium">Message</p>
            <p className="text-gray-700">{event.message || "No message available"}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-semibold">Before</h3>
            <JsonBlock value={event.changes?.before ?? {}} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">After</h3>
            <JsonBlock value={event.changes?.after ?? {}} />
          </div>
        </div>

        <div className="mt-4">
          <h3 className="mb-2 text-sm font-semibold">Metadata</h3>
          <JsonBlock value={event.metadata ?? {}} />
        </div>
      </div>
    </div>
  );
}
