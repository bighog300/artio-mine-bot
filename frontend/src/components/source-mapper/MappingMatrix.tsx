import { useState } from "react";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { MappingRow } from "@/lib/api";
import { MAPPING_ROW_STATUSES } from "@/components/source-mapper/constants";

interface Props {
  rows: MappingRow[];
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  selectedRowIds: string[];
  setSelectedRowIds: (value: string[]) => void;
  onRowUpdate: (
    rowId: string,
    updates: Partial<Pick<MappingRow, "status" | "destination_entity" | "destination_field" | "category_target">>
  ) => void;
}

const DESTINATION_FIELDS: Record<string, string[]> = {
  organization: ["title", "description", "website_url", "url"],
  event: ["title", "description", "start_date", "end_date", "venue_name", "location", "url"],
  exhibition: ["title", "description", "start_date", "end_date", "venue_name", "curator", "url"],
  artist: ["title", "bio", "website_url", "nationality", "birth_year", "death_year", "url"],
  venue: ["title", "description", "address", "city", "country", "website_url", "url"],
  artwork: ["title", "description", "artist_name", "year", "medium", "dimensions", "price", "url"],
};

function CategoryInput({ 
  rowId, 
  initialValue, 
  onUpdate 
}: { 
  rowId: string; 
  initialValue: string | null; 
  onUpdate: (rowId: string, updates: { category_target: string | null; status: string }) => void;
}) {
  const [value, setValue] = useState(initialValue ?? "");

  const handleBlur = () => {
    onUpdate(rowId, { category_target: value || null, status: "needs_review" });
  };

  return (
    <input
      className="w-full border rounded px-2 py-1"
      value={value}
      placeholder="taxonomy/category"
      onChange={(e) => setValue(e.target.value)}
      onBlur={handleBlur}
    />
  );
}

export function MappingMatrix({ rows, statusFilter, onStatusFilterChange, selectedRowIds, setSelectedRowIds, onRowUpdate }: Props) {
  const filteredRows = rows.filter((row) => (statusFilter === "all" ? true : row.status === statusFilter));
  const allVisibleSelected = filteredRows.length > 0 && filteredRows.every((row) => selectedRowIds.includes(row.id));

  return (
    <section className="rounded border bg-card p-4">
      <h2 className="font-semibold mb-3">Mapping Matrix</h2>
      <p className="text-xs text-muted-foreground mb-3">Discovery is generic; choose domain-specific target record types during mapping review.</p>
      <label className="space-y-1 text-sm block mb-3">
        <span>Status filter</span>
        <select className="w-full border rounded px-2 py-1" value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}>
          <option value="all">all</option>
          {MAPPING_ROW_STATUSES.map((status) => (
            <option key={status} value={status}>{status}</option>
          ))}
        </select>
      </label>
      {!rows.length ? <p className="text-sm text-muted-foreground">No mapping rows yet.</p> : (
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="text-left p-2"><input type="checkbox" checked={allVisibleSelected} onChange={(e) => setSelectedRowIds(e.target.checked ? filteredRows.map((row) => row.id) : [])} /></th>
              <th className="text-left p-2">Selector</th>
              <th className="text-left p-2">Sample</th>
              <th className="text-left p-2">Destination</th>
              <th className="text-left p-2">Category</th>
              <th className="text-left p-2">Confidence</th>
              <th className="text-left p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="p-2 align-top"><input type="checkbox" checked={selectedRowIds.includes(row.id)} onChange={(e) => setSelectedRowIds(e.target.checked ? [...selectedRowIds, row.id] : selectedRowIds.filter((id) => id !== row.id))} /></td>
                <td className="p-2">{row.selector}</td>
                <td className="p-2">{row.sample_value ?? "—"}</td>
                <td className="p-2">
                  <div className="flex gap-1">
                    <select
                      className="border rounded px-2 py-1"
                      value={row.destination_entity}
                      onChange={(e) => {
                        const entity = e.target.value;
                        const fallbackField = DESTINATION_FIELDS[entity]?.[0] ?? row.destination_field;
                        onRowUpdate(row.id, { destination_entity: entity, destination_field: fallbackField, status: "needs_review" });
                      }}
                    >
                      {Object.keys(DESTINATION_FIELDS).map((entity) => <option key={entity} value={entity}>{entity}</option>)}
                    </select>
                    <select
                      className="border rounded px-2 py-1"
                      value={row.destination_field}
                      onChange={(e) => onRowUpdate(row.id, { destination_field: e.target.value, status: "needs_review" })}
                    >
                      {(DESTINATION_FIELDS[row.destination_entity] ?? [row.destination_field]).map((field) => <option key={field} value={field}>{field}</option>)}
                    </select>
                  </div>
                </td>
                <td className="p-2">
                  <CategoryInput 
                    rowId={row.id}
                    initialValue={row.category_target}
                    onUpdate={onRowUpdate}
                  />
                </td>
                <td className="p-2"><ConfidenceBadge band={row.confidence_band} score={Math.round(row.confidence_score * 100)} /></td>
                <td className="p-2">
                  <select className="border rounded px-2 py-1" value={row.status} onChange={(e) => onRowUpdate(row.id, { status: e.target.value })}>
                    {MAPPING_ROW_STATUSES.map((status) => (
                      <option key={status} value={status}>{status}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
