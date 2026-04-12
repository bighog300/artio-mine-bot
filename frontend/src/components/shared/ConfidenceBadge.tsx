import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  band: "HIGH" | "MEDIUM" | "LOW";
  score: number;
}

const bandConfig = {
  HIGH: "bg-green-100 text-green-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  LOW: "bg-red-100 text-red-800",
};

export function ConfidenceBadge({ band, score }: ConfidenceBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        bandConfig[band] ?? "bg-gray-100 text-gray-700"
      )}
    >
      {band} · {score}
    </span>
  );
}
