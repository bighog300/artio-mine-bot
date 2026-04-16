interface JobProgressBarProps {
  current?: number;
  total?: number;
  percent?: number | null;
}

export function JobProgressBar({ current = 0, total = 0, percent }: JobProgressBarProps) {
  if (!total || total <= 0) {
    return <span className="text-muted-foreground/80">—</span>;
  }
  const safePercent = Math.max(0, Math.min(100, percent ?? Math.round((current / total) * 100)));
  return (
    <div className="space-y-1 min-w-32">
      <div className="h-2 bg-gray-200 rounded overflow-hidden">
        <div className="h-full bg-blue-600" style={{ width: `${safePercent}%` }} />
      </div>
      <div className="text-xs text-muted-foreground">{current}/{total} ({safePercent}%)</div>
    </div>
  );
}
