interface ScanSettings {
  max_pages: number;
  max_depth: number;
  sample_pages_per_type: number;
  discovery_roots: string[];
  blocked_paths: string[];
}

interface Props {
  sourceUrl: string;
  settings: ScanSettings;
  onSettingsChange: (next: ScanSettings) => void;
  onCreateDraft: () => void;
  onRunScan?: () => void;
  loading?: boolean;
  scanLoading?: boolean;
}

export function ScanSetupForm({ sourceUrl, settings, onSettingsChange, onCreateDraft, onRunScan, loading, scanLoading }: Props) {
  const discoveryRoot = settings.discovery_roots[0] ?? "";
  const blockedPaths = settings.blocked_paths.join(", ");
  return (
    <section className="rounded border bg-card p-4 space-y-3">
      <h2 className="font-semibold">URL Input & Scan Settings</h2>
      <input className="w-full border rounded px-3 py-2 text-sm" value={sourceUrl} disabled />
      <div className="grid grid-cols-3 gap-2 text-sm">
        <label className="space-y-1">Max pages
          <input type="number" className="w-full border rounded px-2 py-1" value={settings.max_pages} onChange={(e) => onSettingsChange({ ...settings, max_pages: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1">Max depth
          <input type="number" className="w-full border rounded px-2 py-1" value={settings.max_depth} onChange={(e) => onSettingsChange({ ...settings, max_depth: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1">Samples/type
          <input type="number" className="w-full border rounded px-2 py-1" value={settings.sample_pages_per_type} onChange={(e) => onSettingsChange({ ...settings, sample_pages_per_type: Number(e.target.value || 0) })} />
        </label>
      </div>
      <div className="grid grid-cols-1 gap-2 text-sm">
        <label className="space-y-1">Discovery root
          <input
            className="w-full border rounded px-2 py-1"
            value={discoveryRoot}
            placeholder="https://www.art.co.za/artists/"
            onChange={(e) => onSettingsChange({ ...settings, discovery_roots: e.target.value ? [e.target.value] : [] })}
          />
        </label>
        <label className="space-y-1">Ignore path patterns (comma separated)
          <input
            className="w-full border rounded px-2 py-1"
            value={blockedPaths}
            placeholder="/watchlist, /my, /auctions"
            onChange={(e) =>
              onSettingsChange({
                ...settings,
                blocked_paths: e.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              })
            }
          />
        </label>
      </div>
      <div className="flex gap-2">
        <button className="px-3 py-2 bg-blue-600 text-white rounded disabled:opacity-60" onClick={onCreateDraft} disabled={loading}>
          {loading ? "Creating..." : "Create Source Scan"}
        </button>
        {onRunScan && (
          <button className="px-3 py-2 bg-primary text-white rounded disabled:opacity-60" onClick={onRunScan} disabled={scanLoading}>
            {scanLoading ? "Running scan..." : "Re-scan"}
          </button>
        )}
      </div>
    </section>
  );
}
