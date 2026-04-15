import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { MappingRow } from "@/lib/api";

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
  event: ["title", "description", "start_date", "end_date", "venue_name", "location", "url"],
  exhibition: ["title", "description", "start_date", "end_date", "venue_name", "curator", "url"],
  artist: ["title", "bio", "website_url", "nationality", "birth_year", "death_year", "url"],
  venue: ["title", "description", "address", "city", "country", "website_url", "url"],
  artwork: ["title", "description", "artist_name", "year", "medium", "dimensions", "price", "url"],
};

export function MappingMatrix({ rows, statusFilter, onStatusFilterChange, selectedRowIds, setSelectedRowIds, onRowUpdate }: Props) {
  const filteredRows = rows.filter((row) => (statusFilter === "all" ? true : row.status === statusFilter));
  const allVisibleSelected = filteredRows.length > 0 && filteredRows.every((row) => selectedRowIds.includes(row.id));

  return (
    <section className="rounded border bg-white p-4">
      <h2 className="font-semibold mb-3">Mapping Matrix</h2>
      <label className="space-y-1 text-sm block mb-3">
        <span>Status filter</span>
        <select className="w-full border rounded px-2 py-1" value={statusFilter} onChange={(e) => onStatusFilterChange(e.target.value)}>
          <option value="all">all</option>
          <option value="proposed">proposed</option>
          <option value="needs_review">needs_review</option>
          <option value="changed_from_published">changed_from_published</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="ignored">ignored</option>
        </select>
      </label>
      {!rows.length ? <p className="text-sm text-gray-500">No mapping rows yet.</p> : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
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
                  <input
                    className="w-full border rounded px-2 py-1"
                    value={row.category_target ?? ""}
                    placeholder="taxonomy/category"
                    onBlur={(e) => onRowUpdate(row.id, { category_target: e.target.value || null, status: "needs_review" })}
                  />
                </td>
                <td className="p-2"><ConfidenceBadge band={row.confidence_band} score={Math.round(row.confidence_score * 100)} /></td>
                <td className="p-2">
                  <select className="border rounded px-2 py-1" value={row.status} onChange={(e) => onRowUpdate(row.id, { status: e.target.value })}>
                    <option value="proposed">proposed</option>
                    <option value="needs_review">needs_review</option>
                    <option value="changed_from_published">changed_from_published</option>
                    <option value="approved">approved</option>
                    <option value="rejected">rejected</option>
                    <option value="ignored">ignored</option>
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
