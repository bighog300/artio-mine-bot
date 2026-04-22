import { cn } from "@/lib/utils";

type ConflictStatus = "none" | "minor" | "major";

interface ConflictBadgeProps {
  status: ConflictStatus;
}

const styles: Record<ConflictStatus, string> = {
  none: "bg-emerald-100 text-emerald-800",
  minor: "bg-amber-100 text-amber-900",
  major: "bg-red-100 text-red-800",
};

export function ConflictBadge({ status }: ConflictBadgeProps) {
  return <span className={cn("inline-flex rounded px-2 py-1 text-xs font-medium capitalize", styles[status])}>{status}</span>;
}
