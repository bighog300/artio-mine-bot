import { useId } from "react";
import { cn } from "@/lib/utils";
import type { InputProps } from "@/types/ui";

export function Input({ label, error, hint, id, className, ...props }: InputProps) {
  const fallbackId = useId();
  const inputId = id ?? fallbackId;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      {label ? (
        <label htmlFor={inputId} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border px-3 py-2 text-sm shadow-sm outline-none transition-colors placeholder:text-gray-400 focus-visible:ring-2 focus-visible:ring-offset-1",
          error
            ? "border-red-500 focus-visible:ring-red-500"
            : "border-gray-300 focus-visible:border-blue-500 focus-visible:ring-blue-500",
          className,
        )}
        {...props}
      />
      {error ? <p id={`${inputId}-error`} className="text-xs text-red-600">{error}</p> : null}
      {!error && hint ? <p id={`${inputId}-hint`} className="text-xs text-gray-500">{hint}</p> : null}
    </div>
  );
}
