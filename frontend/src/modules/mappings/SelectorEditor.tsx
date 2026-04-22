import { ArrowRight } from "lucide-react";
import type { MappingTestResponse } from "@/lib/api";
import { Button, Input } from "@/components/ui";

interface SelectorEditorProps {
  fieldName: string;
  selector: string;
  testing: boolean;
  saving: boolean;
  canSave: boolean;
  baselineRate?: number;
  testRate?: number;
  baselinePreview: MappingTestResponse | null;
  latestPreview: MappingTestResponse | null;
  onChange: (next: string) => void;
  onTest: () => void;
  onSave: () => void;
}

function toValueMap(result: MappingTestResponse | null): Record<string, string> {
  if (!result) return {};
  return Object.fromEntries(result.output.map((row) => [row.label, row.value ?? "(empty)"]));
}

export function SelectorEditor({
  fieldName,
  selector,
  testing,
  saving,
  canSave,
  baselineRate,
  testRate,
  baselinePreview,
  latestPreview,
  onChange,
  onTest,
  onSave,
}: SelectorEditorProps) {
  const beforeMap = toValueMap(baselinePreview);
  const afterMap = toValueMap(latestPreview);
  const keys = Array.from(new Set([...Object.keys(beforeMap), ...Object.keys(afterMap)])).slice(0, 8);

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <h2 className="text-lg font-semibold">Selector Editor</h2>
      <p className="text-sm text-muted-foreground">
        Editing <span className="font-medium text-foreground">{fieldName}</span>. Run a test preview before saving.
      </p>
      <Input value={selector} onChange={(event) => onChange(event.target.value)} placeholder="e.g. .event-card h2" />
      <div className="flex gap-2">
        <Button onClick={onTest} loading={testing} variant="secondary">Test selector</Button>
        <Button onClick={onSave} loading={saving} disabled={!canSave}>Save mapping update</Button>
      </div>
      {!canSave ? <p className="text-xs text-amber-700">Save is disabled until a selector test runs on the current selector value.</p> : null}

      {typeof baselineRate === "number" && typeof testRate === "number" ? (
        <p className="text-sm font-medium">
          Success rate {testRate >= baselineRate ? "improved" : "changed"} from {Math.round(baselineRate * 100)}% <ArrowRight className="mx-1 inline h-3.5 w-3.5" /> {Math.round(testRate * 100)}%
        </p>
      ) : null}

      {keys.length ? (
        <div>
          <h3 className="text-sm font-semibold">Before vs After extraction</h3>
          <table className="mt-2 w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="p-2 text-left">Field</th>
                <th className="p-2 text-left">Before</th>
                <th className="p-2 text-left">After</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key} className="border-t">
                  <td className="p-2 font-medium">{key}</td>
                  <td className="p-2">{beforeMap[key] ?? "—"}</td>
                  <td className="p-2">{afterMap[key] ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
