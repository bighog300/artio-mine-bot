import { useId } from "react";
import { cn } from "@/lib/utils";
import type { SelectProps } from "@/types/ui";

export function Select({ label, error, hint, options, placeholder, id, className, ...props }: SelectProps) {
  const fallbackId = useId();
  const selectId = id ?? fallbackId;
  const describedBy = error ? `${selectId}-error` : hint ? `${selectId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      {label ? (
        <label htmlFor={selectId} className="block text-sm font-medium text-foreground">
          {label}
        </label>
      ) : null}
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-background",
          error
            ? "border-destructive focus-visible:ring-destructive"
            : "focus-visible:border-primary focus-visible:ring-ring",
          className,
        )}
        {...props}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? <p id={`${selectId}-error`} className="text-xs text-destructive">{error}</p> : null}
      {!error && hint ? <p id={`${selectId}-hint`} className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
