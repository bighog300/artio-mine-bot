import type { MappingFieldHealth } from "@/lib/api";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";

interface FieldHealthTableProps {
  fields: MappingFieldHealth[];
  selectedField: string | null;
  onSelectField: (fieldName: string) => void;
}

const driftTone: Record<string, string> = {
  stable: "text-emerald-600",
  warning: "text-amber-600",
  critical: "text-red-600",
};

export function FieldHealthTable({ fields, selectedField, onSelectField }: FieldHealthTableProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Field Health</h2>
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
          {fields.map((field) => (
            <tr
              key={field.field_name}
              className={`cursor-pointer border-t ${selectedField === field.field_name ? "bg-primary/10" : "hover:bg-muted/30"}`}
              onClick={() => onSelectField(field.field_name)}
            >
              <td className="p-2 font-medium">{field.field_name}</td>
              <td className="p-2 font-mono text-xs">{field.selector}</td>
              <td className="p-2">{Math.round(field.success_rate * 100)}%</td>
              <td className="p-2 min-w-[220px]"><ConfidenceBar score={Math.round(field.confidence_avg * 100)} /></td>
              <td className={`p-2 font-medium ${driftTone[field.drift_indicator] ?? "text-muted-foreground"}`}>
                {field.drift_indicator}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
