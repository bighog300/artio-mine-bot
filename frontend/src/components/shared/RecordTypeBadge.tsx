import { cn } from "@/lib/utils";

interface RecordTypeBadgeProps {
  type: string;
}

const typeConfig: Record<string, string> = {
  event: "bg-blue-100 text-blue-800",
  exhibition: "bg-amber-100 text-amber-800",
  artist: "bg-purple-100 text-purple-800",
  venue: "bg-green-100 text-green-800",
  artwork: "bg-pink-100 text-pink-800",
  unknown: "bg-gray-100 text-gray-700",
};

export function RecordTypeBadge({ type }: RecordTypeBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase",
        typeConfig[type] ?? "bg-gray-100 text-gray-700"
      )}
    >
      {type}
    </span>
  );
}
