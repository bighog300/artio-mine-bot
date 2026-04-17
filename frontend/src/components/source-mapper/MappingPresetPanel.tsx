import type { SourceMappingPreset } from "@/lib/api";

interface Props {
  presets: SourceMappingPreset[];
  loading: boolean;
  deletingPresetId: string | null;
  applyingPresetId: string | null;
  onOpenCreate: () => void;
  onDelete: (presetId: string) => void;
  onApply: (presetId: string) => void;
  canCreate: boolean;
}

export function MappingPresetPanel({
  presets,
  loading,
  deletingPresetId,
  applyingPresetId,
  onOpenCreate,
  onDelete,
  onApply,
  canCreate,
}: Props) {
  return (
    <section className="rounded border bg-card p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Mapping Presets</h2>
        <button className="px-3 py-1 rounded bg-foreground text-white text-sm disabled:opacity-60" onClick={onOpenCreate} disabled={!canCreate}>Save as Preset</button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading presets...</p>
      ) : presets.length === 0 ? (
        <p className="text-sm text-muted-foreground">No presets yet for this source.</p>
      ) : (
        <ul className="space-y-2">
          {presets.map((preset) => (
            <li key={preset.id} className="rounded border p-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{preset.name}</div>
                  {preset.description ? <div className="text-xs text-muted-foreground">{preset.description}</div> : null}
                  <div className="mt-1 text-xs text-muted-foreground">
                    Rows: <strong>{preset.row_count}</strong> · Page types: <strong>{preset.page_type_count}</strong>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {preset.created_from_mapping_version_id ? `From version: ${preset.created_from_mapping_version_id}` : "From current draft"} · Created {new Date(preset.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    onClick={() => onApply(preset.id)}
                    disabled={applyingPresetId === preset.id}
                  >
                    {applyingPresetId === preset.id ? "Applying..." : "Apply"}
                  </button>
                  <button
                    className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    onClick={() => onDelete(preset.id)}
                    disabled={deletingPresetId === preset.id}
                  >
                    {deletingPresetId === preset.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
