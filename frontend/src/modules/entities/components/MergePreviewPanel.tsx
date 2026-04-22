interface MergePreviewPanelProps {
  resultingFields: Record<string, string>;
  relationships: Array<{ type: string; count: number }>;
}

export function MergePreviewPanel({ resultingFields, relationships }: MergePreviewPanelProps) {
  return (
    <div className="space-y-3 rounded-lg border bg-card p-4">
      <h3 className="text-lg font-semibold">Merge Preview</h3>
      <div className="grid gap-2 md:grid-cols-2">
        {Object.entries(resultingFields).map(([field, value]) => (
          <div key={field} className="rounded border p-2">
            <p className="text-xs uppercase text-muted-foreground">{field}</p>
            <p className="text-sm">{value || "—"}</p>
          </div>
        ))}
      </div>
      <div>
        <p className="text-sm font-medium">Combined relationships</p>
        <ul className="mt-1 list-disc pl-5 text-sm text-muted-foreground">
          {relationships.map((item) => (
            <li key={item.type}>Will merge {item.count} {item.type}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
