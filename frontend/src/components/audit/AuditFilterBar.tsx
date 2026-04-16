import { Download } from "lucide-react";
import { Button, Input, Select } from "@/components/ui";

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
        <Input
          placeholder="Search message, entity, user"
          value={filters.search}
          onChange={(e) => patch({ search: e.target.value })}
        />
        <Select
          value={filters.event_type}
          onChange={(e) => patch({ event_type: e.target.value })}
          options={[{ value: "", label: "All events" }, ...EVENT_TYPES.map((value) => ({ value, label: value }))]}
        />
        <Select
          value={filters.entity_type}
          onChange={(e) => patch({ entity_type: e.target.value })}
          options={[{ value: "", label: "All entities" }, ...ENTITY_TYPES.map((value) => ({ value, label: value }))]}
        />
        <Input
          placeholder="User ID"
          value={filters.user_id}
          onChange={(e) => patch({ user_id: e.target.value })}
        />
        <Input type="date" value={filters.date_from} onChange={(e) => patch({ date_from: e.target.value })} />
        <Input type="date" value={filters.date_to} onChange={(e) => patch({ date_to: e.target.value })} />
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <Button
          onClick={() => onChange({ event_type: "", entity_type: "", user_id: "", date_from: "", date_to: "", search: "" })}
          variant="secondary"
        >
          Reset
        </Button>
        <Button
          onClick={onExport}
          disabled={isExporting}
          variant="primary"
          icon={<Download className="h-4 w-4" />}
          loading={isExporting}
        >
          {isExporting ? "Exporting..." : "Export CSV"}
        </Button>
      </div>
    </div>
  );
}

export type { AuditFilters };
