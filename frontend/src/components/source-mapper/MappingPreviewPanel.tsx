import type { MappingPreviewResponse } from "@/lib/api";

interface Props {
  preview?: MappingPreviewResponse;
}

export function MappingPreviewPanel({ preview }: Props) {
  return (
    <section className="rounded border bg-white p-4 space-y-2">
      <h2 className="font-semibold">Preview</h2>
      {!preview ? <p className="text-sm text-gray-500">No preview data yet.</p> : (
        <>
          <p className="text-xs text-gray-500">{preview.page_url}</p>
          <pre className="text-xs bg-slate-50 rounded p-2 overflow-auto">{JSON.stringify(preview.record_preview, null, 2)}</pre>
          {preview.warnings.length > 0 && (
            <ul className="text-xs text-amber-700 list-disc pl-4">
              {preview.warnings.map((warning, i) => <li key={`${warning}-${i}`}>{warning}</li>)}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
