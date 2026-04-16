import { cn } from "@/lib/utils";
import type { BadgeVariant } from "@/types/ui";

interface AlertProps {
  title: string;
  description?: string;
  variant?: Exclude<BadgeVariant, "default">;
  className?: string;
}

const variantStyles: Record<Exclude<BadgeVariant, "default">, string> = {
  success: "border-green-200 bg-green-50 text-green-900",
  warning: "border-yellow-200 bg-yellow-50 text-yellow-900",
  error: "border-red-200 bg-red-50 text-red-900",
  info: "border-blue-200 bg-blue-50 text-blue-900",
};

export function Alert({ title, description, variant = "info", className }: AlertProps) {
  return (
    <div role="alert" className={cn("rounded-md border px-4 py-3", variantStyles[variant], className)}>
      <p className="font-medium">{title}</p>
      {description ? <p className="mt-1 text-sm opacity-90">{description}</p> : null}
    </div>
  );
}
