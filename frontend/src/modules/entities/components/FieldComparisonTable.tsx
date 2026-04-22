import { cn } from "@/lib/utils";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";

interface ConflictComparisonRow {
  source: string;
  value: string;
  confidence: number;
}

interface MergeComparisonRow {
  field: string;
  valueA: string;
  valueB: string;
}

interface FieldComparisonTableProps {
  mode: "conflict" | "merge";
  rows: ConflictComparisonRow[] | MergeComparisonRow[];
  leftLabel?: string;
  rightLabel?: string;
}

function isDifferent(a: string, b: string) {
  return a.trim() !== b.trim();
}

export function FieldComparisonTable({ mode, rows, leftLabel = "Entity A", rightLabel = "Entity B" }: FieldComparisonTableProps) {
  if (rows.length === 0) {
    return <div className="rounded border bg-card p-4 text-sm text-muted-foreground">No comparable fields available.</div>;
  }

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-left">
          {mode === "conflict" ? (
            <tr>
              <th className="p-3">Source</th>
              <th className="p-3">Value</th>
              <th className="p-3">Confidence</th>
            </tr>
          ) : (
            <tr>
              <th className="p-3">Field</th>
              <th className="p-3">{leftLabel}</th>
              <th className="p-3">{rightLabel}</th>
            </tr>
          )}
        </thead>
        <tbody>
          {mode === "conflict"
            ? (rows as ConflictComparisonRow[]).map((row, idx) => (
                <tr key={`${row.source}-${idx}`} className="border-t">
                  <td className="p-3 font-medium">{row.source}</td>
                  <td className="p-3">{row.value || "—"}</td>
                  <td className={cn("p-3 min-w-[220px]", row.confidence < 60 ? "bg-red-50/70" : "")}> <ConfidenceBar score={row.confidence} /> </td>
                </tr>
              ))
            : (rows as MergeComparisonRow[]).map((row) => {
                const different = isDifferent(row.valueA ?? "", row.valueB ?? "");
                return (
                  <tr key={row.field} className={cn("border-t", different ? "bg-amber-50/40" : "")}> 
                    <td className="p-3 font-medium">{row.field}</td>
                    <td className={cn("p-3", different ? "font-medium" : "")}>{row.valueA || "—"}</td>
                    <td className={cn("p-3", different ? "font-medium" : "")}>{row.valueB || "—"}</td>
                  </tr>
                );
              })}
        </tbody>
      </table>
    </div>
  );
}
