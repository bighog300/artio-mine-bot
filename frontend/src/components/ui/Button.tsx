import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/Spinner";
import type { ButtonProps } from "@/types/ui";

const variantStyles = {
  primary: "bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-ring",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 focus-visible:ring-ring",
  danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive",
  ghost: "bg-transparent text-foreground hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring",
};

const sizeStyles = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
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
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60",
        variantStyles[variant],
        sizeStyles[size],
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
