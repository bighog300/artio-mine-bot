import { cn } from "@/lib/utils";
import type { BadgeVariant } from "@/types/ui";

interface BadgeProps {
  variant?: BadgeVariant;
  children: string;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-muted text-muted-foreground",
  success: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100",
  warning: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
  error: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100",
  info: "bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium", variantStyles[variant], className)}>
      {children}
    </span>
  );
}
