import type { ChangeEvent } from "react";
import type { ChoiceControlProps } from "@/types/ui";

export function Checkbox({ id, name, label, checked, disabled, onChange }: ChoiceControlProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.checked);
  };

  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm text-foreground">
      <input
        id={id}
        type="checkbox"
        name={name}
        checked={checked}
        disabled={disabled}
        onChange={handleChange}
        className="h-4 w-4 rounded border-input bg-background text-primary focus:ring-ring disabled:cursor-not-allowed"
      />
      <span>{label}</span>
    </label>
  );
}
