import type { MappingPreviewResponse } from "@/lib/api";

interface Props {
  preview?: MappingPreviewResponse;
}

export function MappingPreviewPanel({ preview }: Props) {
  return (
    <section className="rounded border bg-card p-4 space-y-2">
      <h2 className="font-semibold">Preview</h2>
      {!preview ? <p className="text-sm text-muted-foreground">No preview data yet.</p> : (
        <>
          <p className="text-xs text-muted-foreground">{preview.page_url}</p>
          {preview.source_snippet && (
            <div>
              <p className="text-xs font-medium text-muted-foreground">Source snippet</p>
              <pre className="text-xs bg-muted/40 rounded p-2 overflow-auto max-h-28">{preview.source_snippet}</pre>
            </div>
          )}
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Extraction preview</p>
            <div className="max-h-48 overflow-auto rounded border">
              <table className="w-full text-xs">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="p-2 text-left">Source value</th>
                    <th className="p-2 text-left">Destination</th>
                    <th className="p-2 text-left">Category</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.extractions.map((item) => (
                    <tr key={item.mapping_row_id} className="border-t">
                      <td className="p-2">{item.normalized_value ?? item.raw_value ?? "—"}</td>
                      <td className="p-2">{item.destination_entity}.{item.destination_field}</td>
                      <td className="p-2">{item.category_target ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <pre className="text-xs bg-muted/40 rounded p-2 overflow-auto">{JSON.stringify(preview.record_preview, null, 2)}</pre>
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
