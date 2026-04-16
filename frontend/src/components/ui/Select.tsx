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
        <label htmlFor={selectId} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      ) : null}
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border bg-white px-3 py-2 text-sm shadow-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-1",
          error
            ? "border-red-500 focus-visible:ring-red-500"
            : "border-gray-300 focus-visible:border-blue-500 focus-visible:ring-blue-500",
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
      {error ? <p id={`${selectId}-error`} className="text-xs text-red-600">{error}</p> : null}
      {!error && hint ? <p id={`${selectId}-hint`} className="text-xs text-gray-500">{hint}</p> : null}
    </div>
  );
}
