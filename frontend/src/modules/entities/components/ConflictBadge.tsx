import { cn } from "@/lib/utils";

type ConflictStatus = "none" | "minor" | "medium" | "major";

interface ConflictBadgeProps {
  status: ConflictStatus;
}

const styles: Record<ConflictStatus, string> = {
  none: "bg-emerald-100 text-emerald-800",
  minor: "bg-amber-100 text-amber-900",
  medium: "bg-orange-100 text-orange-900",
  major: "bg-red-100 text-red-800",
};

export function ConflictBadge({ status }: ConflictBadgeProps) {
  return <span className={cn("inline-flex rounded px-2 py-1 text-xs font-medium capitalize", styles[status])}>{status}</span>;
}

interface ConflictSeverityMetrics {
  sourceCount?: number;
  confidenceValues?: number[];
  values?: string[];
}

export function deriveConflictSeverity({ sourceCount = 0, confidenceValues = [], values = [] }: ConflictSeverityMetrics): Exclude<ConflictStatus, "none"> {
  const uniqueValues = new Set(values.filter((value) => value && value.trim().length > 0)).size;
  const confidenceSpread = confidenceValues.length > 1 ? Math.max(...confidenceValues) - Math.min(...confidenceValues) : 0;

  if (sourceCount >= 4 || uniqueValues >= 3 || confidenceSpread >= 0.45) return "major";
  if (sourceCount >= 3 || uniqueValues >= 2 || confidenceSpread >= 0.2) return "medium";
  return "minor";
}
