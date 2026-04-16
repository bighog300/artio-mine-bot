import { Download } from "lucide-react";

interface AuditFilters {
  event_type: string;
  entity_type: string;
  user_id: string;
  date_from: string;
  date_to: string;
  search: string;
}

interface AuditFilterBarProps {
  filters: AuditFilters;
  onChange: (next: AuditFilters) => void;
  onExport: () => void;
  isExporting: boolean;
}

const EVENT_TYPES = ["create", "update", "delete", "approve", "reject", "merge"];
const ENTITY_TYPES = ["source", "record", "page", "job", "system"];

export function AuditFilterBar({ filters, onChange, onExport, isExporting }: AuditFilterBarProps) {
  const patch = (partial: Partial<AuditFilters>) => onChange({ ...filters, ...partial });

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-6">
        <input
          className="rounded border px-3 py-2 text-sm"
          placeholder="Search message, entity, user"
          value={filters.search}
          onChange={(e) => patch({ search: e.target.value })}
        />
        <select className="rounded border px-3 py-2 text-sm" value={filters.event_type} onChange={(e) => patch({ event_type: e.target.value })}>
          <option value="">All events</option>
          {EVENT_TYPES.map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
        <select className="rounded border px-3 py-2 text-sm" value={filters.entity_type} onChange={(e) => patch({ entity_type: e.target.value })}>
          <option value="">All entities</option>
          {ENTITY_TYPES.map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
        <input
          className="rounded border px-3 py-2 text-sm"
          placeholder="User ID"
          value={filters.user_id}
          onChange={(e) => patch({ user_id: e.target.value })}
        />
        <input className="rounded border px-3 py-2 text-sm" type="date" value={filters.date_from} onChange={(e) => patch({ date_from: e.target.value })} />
        <input className="rounded border px-3 py-2 text-sm" type="date" value={filters.date_to} onChange={(e) => patch({ date_to: e.target.value })} />
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button
          type="button"
          onClick={() => onChange({ event_type: "", entity_type: "", user_id: "", date_from: "", date_to: "", search: "" })}
          className="rounded border px-3 py-2 text-sm"
        >
          Reset
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={isExporting}
          className="inline-flex items-center gap-2 rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          <Download className="h-4 w-4" />
          {isExporting ? "Exporting..." : "Export CSV"}
        </button>
      </div>
    </div>
  );
}

export type { AuditFilters };
