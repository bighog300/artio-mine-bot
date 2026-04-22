import { ConfidenceBar } from "@/components/shared/ConfidenceBar";

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
  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Field Confidence</h2>
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
          {rows.map((row) => {
            const status = fieldStatus(row);
            return (
              <tr
                key={row.field}
                className={`border-t ${status === "missing" ? "bg-red-50" : status === "low confidence" ? "bg-amber-50" : ""}`}
              >
                <td className="p-2 font-medium">{row.field}</td>
                <td className="p-2">{row.value || <span className="text-red-600">Missing</span>}</td>
                <td className="p-2 min-w-[220px]"><ConfidenceBar score={Math.round(row.confidence * 100)} /></td>
                <td className={`p-2 ${status === "ok" ? "text-emerald-600" : "text-red-600"}`}>{status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
