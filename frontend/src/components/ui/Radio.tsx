import type { ChangeEvent } from "react";
import type { ChoiceControlProps } from "@/types/ui";

export function Radio({ id, name, label, checked, disabled, onChange }: ChoiceControlProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.checked);
  };

  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-sm text-gray-700">
      <input
        id={id}
        type="radio"
        name={name}
        checked={checked}
        disabled={disabled}
        onChange={handleChange}
        className="h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
      />
      <span>{label}</span>
    </label>
  );
}
