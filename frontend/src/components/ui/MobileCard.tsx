import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface MobileCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

export function MobileCard({ children, className, onClick }: MobileCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "space-y-2 rounded-lg border border-border bg-card p-4",
        "active:bg-muted/40",
        onClick ? "cursor-pointer" : undefined,
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MobileCardRow({
  label,
  value,
  className,
}: {
  label: string;
  value: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between", className)}>
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <span className="ml-4 text-right text-sm text-foreground">{value}</span>
    </div>
  );
}
