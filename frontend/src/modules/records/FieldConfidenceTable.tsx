import { AlertTriangle } from "lucide-react";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { severityRowClass } from "@/lib/severity";

export interface FieldConfidenceRow {
  field: string;
  value: string;
  confidence: number;
}

interface FieldConfidenceTableProps {
  rows: FieldConfidenceRow[];
}

function fieldStatus(row: FieldConfidenceRow): "ok" | "missing" | "low confidence" {
  if (!row.value || row.value.trim().length === 0) return "missing";
  if (row.confidence < 0.6) return "low confidence";
  return "ok";
}

export function FieldConfidenceTable({ rows }: FieldConfidenceTableProps) {
  const sortedRows = [...rows].sort((a, b) => a.confidence - b.confidence);

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Field Confidence</h2>
      {!sortedRows.length ? (
        <p className="mt-3 text-sm text-muted-foreground">No field confidence values are available for this record.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-2 text-left">Field</th>
              <th className="p-2 text-left">Value</th>
              <th className="p-2 text-left">Confidence</th>
              <th className="p-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.slice(0, 100).map((row) => {
              const status = fieldStatus(row);
              const severityClass = status === "missing" ? severityRowClass.critical : status === "low confidence" ? severityRowClass.high : "";
              return (
                <tr key={row.field} className={`border-t ${severityClass}`}>
                  <td className="p-2 font-medium">{row.field}</td>
                  <td className="p-2">
                    {row.value || (
                      <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-amber-900">
                        <AlertTriangle className="h-3.5 w-3.5" /> Missing
                      </span>
                    )}
                  </td>
                  <td className="p-2 min-w-[220px]"><ConfidenceBar score={Math.round(row.confidence * 100)} /></td>
                  <td className={`p-2 capitalize ${status === "ok" ? "text-emerald-600" : "text-red-700"}`}>{status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {sortedRows.length > 100 ? <p className="mt-2 text-xs text-muted-foreground">Showing first 100 lowest-confidence fields.</p> : null}
    </div>
  );
}
