import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/Spinner";
import type { ButtonProps } from "@/types/ui";

const variantStyles = {
  primary: "bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-ring",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 focus-visible:ring-ring",
  danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive",
  ghost: "bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring",
  warning: "bg-warning text-warning-foreground hover:bg-warning/90 focus-visible:ring-warning",
  outline: "border border-border bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring",
} as const;

const sizeStyles = {
  sm: "min-h-[36px] px-3 py-1.5 text-sm",
  md: "min-h-[44px] px-4 py-2 text-base",
  lg: "min-h-[48px] px-6 py-3 text-lg",
} as const;

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  icon,
  className,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex touch-manipulation items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60",
        variantStyles[variant],
        sizeStyles[size],
        fullWidth ? "w-full" : undefined,
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Spinner size="sm" label="Button loading" /> : icon ? <span className="inline-flex">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}
