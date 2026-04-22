import type { MappingTestResponse } from "@/lib/api";

interface ExtractionPreviewProps {
  result: MappingTestResponse | null;
}

export function ExtractionPreview({ result }: ExtractionPreviewProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Extraction Preview</h2>
      {!result ? (
        <p className="mt-2 text-sm text-muted-foreground">Select a field and run a selector test to preview structured output.</p>
      ) : (
        <div className="mt-3 space-y-3">
          <div className="rounded border bg-muted/30 p-3">
            <p className="text-sm font-medium">{result.field_name}</p>
            <p className="text-xs text-muted-foreground font-mono">{result.selector}</p>
          </div>
          <div className="space-y-2">
            {result.output.map((row) => (
              <div key={`${row.label}-${row.value}`} className="rounded border p-3">
                <p className="text-xs uppercase text-muted-foreground">{row.label}</p>
                <p className="text-sm">{row.value ?? "(empty)"}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
