import { cn } from "@/lib/utils";
import type { BadgeVariant } from "@/types/ui";

interface AlertProps {
  title: string;
  description?: string;
  variant?: Exclude<BadgeVariant, "default">;
  className?: string;
}

const variantStyles: Record<Exclude<BadgeVariant, "default">, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100",
  warning: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-900/30 dark:text-amber-100",
  error: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-900/30 dark:text-red-100",
  info: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-900 dark:bg-blue-900/30 dark:text-blue-100",
};

export function Alert({ title, description, variant = "info", className }: AlertProps) {
  return (
    <div role="alert" className={cn("rounded-md border px-4 py-3", variantStyles[variant], className)}>
      <p className="font-medium">{title}</p>
      {description ? <p className="mt-1 text-sm opacity-90">{description}</p> : null}
    </div>
  );
}
