import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  score: number;
  reasons?: string[];
}

export function ConfidenceBar({ score, reasons = [] }: ConfidenceBarProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  const color =
    normalizedScore > 85 ? "bg-green-500" : normalizedScore >= 60 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all", color)}
            style={{ width: `${normalizedScore}%` }}
          />
        </div>
        <span className="text-sm font-medium w-10 text-right">{normalizedScore}</span>
      </div>
      {reasons.length > 0 && (
        <ul className="text-xs text-gray-500 space-y-0.5">
          {reasons.map((r, i) => (
            <li key={i}>• {r}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
