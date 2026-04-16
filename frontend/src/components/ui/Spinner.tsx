import { cn } from "@/lib/utils";
import type { SpinnerProps } from "@/types/ui";

const sizeStyles = {
  sm: "h-4 w-4 border-2",
  md: "h-5 w-5 border-2",
  lg: "h-6 w-6 border-[3px]",
};

export function Spinner({ size = "md", className, label = "Loading" }: SpinnerProps) {
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-live="polite" aria-label={label}>
      <span
        className={cn(
          "inline-block animate-spin rounded-full border-current border-r-transparent text-current",
          sizeStyles[size],
          className,
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}
