export type SeverityLevel = "critical" | "high" | "medium" | "low";

export const severityOrder: SeverityLevel[] = ["critical", "high", "medium", "low"];

export function normalizeSeverity(input: string | null | undefined): SeverityLevel {
  const value = (input ?? "").toLowerCase();
  if (["critical", "stale", "error", "failed"].includes(value)) return "critical";
  if (["high", "degraded", "warning"].includes(value)) return "high";
  if (["medium", "warn"].includes(value)) return "medium";
  return "low";
}

export const severityLabel: Record<SeverityLevel, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const severityBadgeClass: Record<SeverityLevel, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-amber-100 text-amber-800 border-amber-200",
  low: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

export const severityRowClass: Record<SeverityLevel, string> = {
  critical: "bg-red-50 border-l-4 border-red-500",
  high: "bg-orange-50 border-l-4 border-orange-400",
  medium: "bg-amber-50 border-l-4 border-amber-400",
  low: "",
};
