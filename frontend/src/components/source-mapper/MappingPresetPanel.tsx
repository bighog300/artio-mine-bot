import type { SourceMappingPreset } from "@/lib/api";

interface Props {
  presets: SourceMappingPreset[];
  loading: boolean;
  deletingPresetId: string | null;
  onOpenCreate: () => void;
  onDelete: (presetId: string) => void;
  canCreate: boolean;
}

export function MappingPresetPanel({ presets, loading, deletingPresetId, onOpenCreate, onDelete, canCreate }: Props) {
  return (
    <section className="rounded border bg-white p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Mapping Presets</h2>
        <button className="px-3 py-1 rounded bg-slate-900 text-white text-sm disabled:opacity-60" onClick={onOpenCreate} disabled={!canCreate}>Save as Preset</button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading presets...</p>
      ) : presets.length === 0 ? (
        <p className="text-sm text-gray-500">No presets yet for this source.</p>
      ) : (
        <ul className="space-y-2">
          {presets.map((preset) => (
            <li key={preset.id} className="rounded border p-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{preset.name}</div>
                  {preset.description ? <div className="text-xs text-gray-600">{preset.description}</div> : null}
                  <div className="mt-1 text-xs text-gray-500">
                    Rows: <strong>{preset.row_count}</strong> · Page types: <strong>{preset.page_type_count}</strong>
                  </div>
                  <div className="text-xs text-gray-500">
                    {preset.created_from_mapping_version_id ? `From version: ${preset.created_from_mapping_version_id}` : "From current draft"} · Created {new Date(preset.created_at).toLocaleString()}
                  </div>
                </div>
                <button
                  className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                  onClick={() => onDelete(preset.id)}
                  disabled={deletingPresetId === preset.id}
                >
                  {deletingPresetId === preset.id ? "Deleting..." : "Delete"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
