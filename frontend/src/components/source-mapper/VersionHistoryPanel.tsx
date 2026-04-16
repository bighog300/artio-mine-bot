import type { MappingDiffSummary, MappingVersion } from "@/lib/api";

interface Props {
  versions: MappingVersion[];
  diff?: MappingDiffSummary;
  onPublish: () => void;
  publishing: boolean;
  onRollback: (versionId: string) => void;
}

export function VersionHistoryPanel({ versions, diff, onPublish, publishing, onRollback }: Props) {
  return (
    <section className="rounded border bg-card p-4 space-y-2">
      <h2 className="font-semibold">Versioning & Publish</h2>
      <div className="text-sm">
        {diff ? (
          <span>Diff — Added: <strong>{diff.added}</strong>, Changed: <strong>{diff.changed}</strong>, Removed: <strong>{diff.removed}</strong>, Unchanged: <strong>{diff.unchanged}</strong></span>
        ) : "Loading diff..."}
      </div>
      <button className="px-3 py-2 bg-emerald-600 text-white rounded disabled:opacity-60" onClick={onPublish} disabled={publishing}>
        {publishing ? "Publishing..." : "Publish Draft"}
      </button>
      <div className="text-sm">
        <div className="font-medium mb-1">Recent versions</div>
        {!versions.length ? "No versions yet." : (
          <ul className="space-y-1">
            {versions.slice(0, 6).map((version) => (
              <li key={version.id} className="text-xs border rounded p-2 flex justify-between items-center gap-2">
                <span>
                  v{version.version_number} — <strong>{version.status}</strong> {version.published_at ? `(published ${new Date(version.published_at).toLocaleString()})` : ""}
                </span>
                {version.status === "published" && (
                  <button className="px-2 py-1 border rounded" onClick={() => onRollback(version.id)}>Rollback</button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
