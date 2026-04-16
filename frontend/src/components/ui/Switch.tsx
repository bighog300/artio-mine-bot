import type { ChangeEvent } from "react";
import { cn } from "@/lib/utils";
import type { SwitchProps } from "@/types/ui";

export function Switch({ id, label, checked = false, disabled, onChange }: SwitchProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    onChange?.(event.target.checked);
  };

  return (
    <label htmlFor={id} className="inline-flex items-center gap-3 text-sm text-gray-700">
      <span>{label}</span>
      <span className="relative inline-flex items-center">
        <input id={id} type="checkbox" className="peer sr-only" checked={checked} onChange={handleChange} disabled={disabled} />
        <span
          aria-hidden
          className={cn(
            "h-6 w-11 rounded-full transition-colors",
            checked ? "bg-blue-600" : "bg-gray-300",
            disabled ? "opacity-60" : "",
          )}
        />
        <span
          aria-hidden
          className={cn(
            "absolute left-0.5 h-5 w-5 rounded-full bg-white transition-transform",
            checked ? "translate-x-5" : "translate-x-0",
          )}
        />
      </span>
    </label>
  );
}
