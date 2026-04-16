import type { MiningStatus } from "@/lib/api";

interface MiningProgressProps {
  status: MiningStatus["status"];
  progress?: MiningStatus["progress"] | null;
  errorMessage?: string | null;
  onRetry?: () => void;
  retryPending?: boolean;
}

const TERMINAL_STATUSES = new Set(["done", "error", "paused", "stopped"]);

export function MiningProgress({
  status,
  progress,
  errorMessage,
  onRetry,
  retryPending = false,
}: MiningProgressProps) {
  const percent = progress?.percent_complete ?? 0;
  const totalPages = progress?.pages_total_estimated ?? 0;
  const pagesCrawled = progress?.pages_crawled ?? 0;
  const recordsExtracted = progress?.records_extracted ?? 0;

  const waitingForWorker =
    status === "queued" &&
    pagesCrawled === 0 &&
    recordsExtracted === 0 &&
    !TERMINAL_STATUSES.has(status);

  return (
    <div className="bg-card border rounded p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Mining progress</h3>
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{status}</span>
      </div>

      <div className="h-2 w-full bg-muted rounded overflow-hidden">
        <div className="h-full bg-blue-600 transition-all duration-300" style={{ width: `${percent}%` }} />
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
        <div>
          <div className="font-medium text-foreground">{percent}%</div>
          <div>Complete</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{pagesCrawled}/{totalPages}</div>
          <div>Pages crawled</div>
        </div>
        <div>
          <div className="font-medium text-foreground">{recordsExtracted}</div>
          <div>Records extracted</div>
        </div>
      </div>

      {waitingForWorker && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          Waiting for worker...
        </p>
      )}

      {status === "done" && (
        <p className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">
          Mining completed successfully!
        </p>
      )}

      {status === "error" && (
        <div className="space-y-2">
          <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">
            {errorMessage ?? "Mining failed. Please retry."}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              disabled={retryPending}
              className="px-2 py-1 text-xs border border-red-300 text-red-700 rounded disabled:opacity-60"
            >
              {retryPending ? "Retrying..." : "Retry"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
