interface Conflict {
  field: string;
  value_a: unknown;
  value_b: unknown;
}

interface MergeControlPanelProps {
  conflicts: Conflict[];
  strategy: Record<string, "a" | "b" | "both">;
  onChange: (field: string, choice: "a" | "b" | "both") => void;
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value);
}

export function MergeControlPanel({ conflicts, strategy, onChange }: MergeControlPanelProps) {
  if (conflicts.length === 0) {
    return (
      <section className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
        <h3 className="text-green-700 font-medium">No conflicts detected</h3>
        <p className="text-sm text-green-600 mt-1">All important fields align. You can merge immediately.</p>
      </section>
    );
  }

  return (
    <section className="bg-white border rounded-lg p-4">
      <h3 className="font-semibold mb-4">Resolve Conflicts ({conflicts.length})</h3>

      <div className="space-y-4">
        {conflicts.map(({ field, value_a, value_b }) => {
          const optionA = stringifyValue(value_a);
          const optionB = stringifyValue(value_b);
          const optionBoth = optionA === "—" ? optionB : optionB === "—" ? optionA : `${optionA}; ${optionB}`;

          return (
            <fieldset key={field} className="border rounded-lg p-3">
              <legend className="font-medium text-sm mb-3 capitalize px-1">{field.replace(/_/g, " ")}</legend>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <label className="flex items-start gap-2 cursor-pointer border rounded p-2">
                  <input
                    type="radio"
                    aria-label={`${field} record a`}
                    name={`merge-${field}`}
                    checked={strategy[field] === "a"}
                    onChange={() => onChange(field, "a")}
                    className="mt-1"
                  />
                  <div className="flex-1 text-sm">
                    <div className="font-medium text-blue-600">Record A</div>
                    <div className="mt-1 text-gray-700 break-words">{optionA}</div>
                  </div>
                </label>

                <label className="flex items-start gap-2 cursor-pointer border rounded p-2">
                  <input
                    type="radio"
                    aria-label={`${field} record b`}
                    name={`merge-${field}`}
                    checked={strategy[field] === "b"}
                    onChange={() => onChange(field, "b")}
                    className="mt-1"
                  />
                  <div className="flex-1 text-sm">
                    <div className="font-medium text-purple-600">Record B</div>
                    <div className="mt-1 text-gray-700 break-words">{optionB}</div>
                  </div>
                </label>

                <label className="flex items-start gap-2 cursor-pointer border rounded p-2">
                  <input
                    type="radio"
                    aria-label={`${field} combine`}
                    name={`merge-${field}`}
                    checked={strategy[field] === "both"}
                    onChange={() => onChange(field, "both")}
                    className="mt-1"
                  />
                  <div className="flex-1 text-sm">
                    <div className="font-medium text-green-600">Combine</div>
                    <div className="mt-1 text-gray-700 text-xs break-words">{optionBoth}</div>
                  </div>
                </label>
              </div>
            </fieldset>
          );
        })}
      </div>
    </section>
  );
}
