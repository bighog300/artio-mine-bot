import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { MappingTestResponse } from "@/lib/api";

interface ExtractionPreviewProps {
  result: MappingTestResponse | null;
  confidenceByField?: Record<string, number>;
}

function statusForValue(value: string | null) {
  if (value === null || value.trim().length === 0) return "failed" as const;
  return "ok" as const;
}

export function ExtractionPreview({ result, confidenceByField = {} }: ExtractionPreviewProps) {
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
          {!result.output.length ? (
            <p className="text-sm text-muted-foreground">No extracted rows were returned from this test.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="p-2 text-left">Field</th>
                  <th className="p-2 text-left">Extracted Value</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="p-2 text-left">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.output.map((row) => {
                  const status = statusForValue(row.value);
                  const confidence = confidenceByField[row.label];
                  return (
                    <tr key={`${row.label}-${row.value}`} className={`border-t ${status === "failed" ? "bg-red-50 border-l-4 border-red-500" : ""}`}>
                      <td className="p-2 font-medium">{row.label}</td>
                      <td className="p-2">{row.value ?? <span className="text-red-700">(empty)</span>}</td>
                      <td className="p-2">
                        <span className={`inline-flex items-center gap-1 ${status === "failed" ? "text-red-700" : "text-emerald-700"}`}>
                          {status === "failed" ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                          {status}
                        </span>
                      </td>
                      <td className="p-2">{typeof confidence === "number" ? `${Math.round(confidence * 100)}%` : "n/a"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
