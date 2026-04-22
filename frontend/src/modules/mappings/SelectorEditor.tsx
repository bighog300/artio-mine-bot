import { Button, Input } from "@/components/ui";

interface SelectorEditorProps {
  fieldName: string;
  selector: string;
  testing: boolean;
  saving: boolean;
  onChange: (next: string) => void;
  onTest: () => void;
  onSave: () => void;
}

export function SelectorEditor({ fieldName, selector, testing, saving, onChange, onTest, onSave }: SelectorEditorProps) {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <h2 className="text-lg font-semibold">Selector Editor</h2>
      <p className="text-sm text-muted-foreground">
        Editing <span className="font-medium text-foreground">{fieldName}</span>. Test first, then save when extraction output looks correct.
      </p>
      <Input value={selector} onChange={(event) => onChange(event.target.value)} placeholder="e.g. .event-card h2" />
      <div className="flex gap-2">
        <Button onClick={onTest} loading={testing} variant="secondary">Test selector</Button>
        <Button onClick={onSave} loading={saving}>Save mapping update</Button>
      </div>
    </div>
  );
}
