import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
}

const statusConfig: Record<string, { label: string; className: string; pulse?: boolean }> = {
  done: { label: "Done", className: "bg-green-100 text-green-800" },
  approved: { label: "Approved", className: "bg-green-100 text-green-800" },
  exported: { label: "Exported", className: "bg-green-100 text-green-800" },
  running: { label: "Running", className: "bg-blue-100 text-blue-800", pulse: true },
  crawling: { label: "Crawling", className: "bg-blue-100 text-blue-800", pulse: true },
  extracting: { label: "Extracting", className: "bg-purple-100 text-purple-800", pulse: true },
  mapping: { label: "Mapping", className: "bg-blue-100 text-blue-800", pulse: true },
  pending: { label: "Pending", className: "bg-gray-100 text-gray-700" },
  paused: { label: "Paused", className: "bg-yellow-100 text-yellow-800" },
  error: { label: "Error", className: "bg-red-100 text-red-800" },
  rejected: { label: "Rejected", className: "bg-red-100 text-red-800" },
  failed: { label: "Failed", className: "bg-red-100 text-red-800" },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] ?? { label: status, className: "bg-gray-100 text-gray-700" };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        config.className,
        config.pulse && "animate-pulse"
      )}
    >
      {config.label}
    </span>
  );
}
