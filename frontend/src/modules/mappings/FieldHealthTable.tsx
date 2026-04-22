import { AlertTriangle } from "lucide-react";
import type { MappingFieldHealth } from "@/lib/api";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { normalizeSeverity, severityRowClass } from "@/lib/severity";

interface FieldHealthTableProps {
  fields: MappingFieldHealth[];
  selectedField: string | null;
  onSelectField: (fieldName: string) => void;
}

function getFieldSeverity(field: MappingFieldHealth) {
  if (field.confidence_avg < 0.6 || field.drift_indicator === "critical") return "critical" as const;
  if (field.success_rate < 0.75 || field.drift_indicator === "warning") return "high" as const;
  if (field.success_rate < 0.9) return "medium" as const;
  return normalizeSeverity(field.drift_indicator);
}

export function FieldHealthTable({ fields, selectedField, onSelectField }: FieldHealthTableProps) {
  const sortedFields = [...fields].sort((a, b) => {
    const aScore = a.confidence_avg * 0.7 + a.success_rate * 0.3;
    const bScore = b.confidence_avg * 0.7 + b.success_rate * 0.3;
    return aScore - bScore;
  });

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Field Health</h2>
      {!sortedFields.length ? (
        <p className="mt-3 text-sm text-muted-foreground">No field health data available yet.</p>
      ) : (
        <table className="mt-3 w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-2 text-left">Field</th>
              <th className="p-2 text-left">Selector</th>
              <th className="p-2 text-left">Success rate</th>
              <th className="p-2 text-left">Confidence avg</th>
              <th className="p-2 text-left">Drift</th>
            </tr>
          </thead>
          <tbody>
            {sortedFields.slice(0, 100).map((field) => {
              const severity = getFieldSeverity(field);
              const isMissing = field.success_rate <= 0;
              return (
                <tr
                  key={field.field_name}
                  className={`cursor-pointer border-t ${severityRowClass[severity]} ${selectedField === field.field_name ? "ring-1 ring-primary" : "hover:bg-muted/30"}`}
                  onClick={() => onSelectField(field.field_name)}
                >
                  <td className="p-2 font-medium">{field.field_name}</td>
                  <td className="p-2 font-mono text-xs">{field.selector}</td>
                  <td className="p-2">{Math.round(field.success_rate * 100)}%</td>
                  <td className="p-2 min-w-[220px]"><ConfidenceBar score={Math.round(field.confidence_avg * 100)} /></td>
                  <td className="p-2 font-medium capitalize">
                    <span className="inline-flex items-center gap-1">
                      {isMissing ? <AlertTriangle className="h-3.5 w-3.5 text-amber-700" /> : null}
                      {field.drift_indicator}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {sortedFields.length > 100 ? <p className="mt-2 text-xs text-muted-foreground">Showing first 100 worst fields.</p> : null}
    </div>
  );
}
