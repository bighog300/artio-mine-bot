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
        <label htmlFor={inputId} className="block text-sm font-medium text-foreground">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-required={props.required}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-background",
          error
            ? "border-destructive focus-visible:ring-destructive"
            : "focus-visible:border-primary focus-visible:ring-ring",
          className,
        )}
        {...props}
      />
      {error ? <p id={`${inputId}-error`} role="alert" className="text-xs text-destructive">{error}</p> : null}
      {!error && hint ? <p id={`${inputId}-hint`} className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
