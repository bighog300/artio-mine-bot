import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle, Loader2, RefreshCw } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { Alert, Button, Skeleton } from "@/components/ui";
import { getSmartMineStatus } from "@/lib/api";

const STAGES = ["analyzing", "generating", "testing", "mining"] as const;
type Stage = (typeof STAGES)[number];

const STAGE_LABELS: Record<Stage, string> = {
  analyzing: "Analyzing site",
  generating: "Generating strategy",
  testing: "Testing extraction",
  mining: "Mining data",
};

function getCurrentStage(status?: string | null, stage?: string | null): Stage {
  if (stage && STAGES.includes(stage as Stage)) {
    return stage as Stage;
  }

  const normalizedStatus = (status ?? "").toLowerCase();
  if (normalizedStatus.includes("analy")) return "analyzing";
  if (normalizedStatus.includes("generat")) return "generating";
  if (normalizedStatus.includes("test")) return "testing";
  return "mining";
}

function isComplete(status?: string | null): boolean {
  const normalized = (status ?? "").toLowerCase();
  return normalized === "done" || normalized === "completed" || normalized === "success";
}

function isError(status?: string | null): boolean {
  const normalized = (status ?? "").toLowerCase();
  return normalized === "error" || normalized === "failed";
}

export function SmartMiningProgress() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const navigate = useNavigate();

  const statusQuery = useQuery({
    queryKey: ["smart-mine-status", sourceId],
    queryFn: () => getSmartMineStatus(sourceId ?? ""),
    enabled: Boolean(sourceId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || isComplete(status) || isError(status)) {
        return false;
      }
      return 2000;
    },
  });

  const status = statusQuery.data;
  const currentStage = getCurrentStage(status?.status, status?.stage);
  const currentStageIndex = STAGES.indexOf(currentStage);
  const completed = isComplete(status?.status);
  const failed = isError(status?.status);

  const progressPercent = useMemo(() => {
    if (!status) return 0;
    if (typeof status.progress_percent === "number") return status.progress_percent;
    if (typeof status.progress?.percent_complete === "number") return status.progress.percent_complete;
    if (completed) return 100;
    return Math.round(((currentStageIndex + 1) / STAGES.length) * 100);
  }, [completed, currentStageIndex, status]);

  if (!sourceId) {
    return <Alert variant="error" title="Missing source ID" description="Open this page from Smart Mining start page." />;
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold lg:text-3xl">Smart Mining Progress</h1>
          <p className="text-sm text-muted-foreground">Source: {sourceId}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => statusQuery.refetch()} icon={<RefreshCw className="h-4 w-4" />}>
          Refresh
        </Button>
      </div>

      {statusQuery.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-32 rounded-lg border" />
          <Skeleton className="h-24 rounded-lg border" />
        </div>
      ) : statusQuery.isError ? (
        <Alert
          variant="error"
          title="Unable to fetch Smart Mining status"
          description={statusQuery.error instanceof Error ? statusQuery.error.message : "Please retry."}
        />
      ) : (
        <>
          <section className="rounded-lg border bg-card p-4 lg:p-6">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-medium">Overall progress</p>
              <p className="text-sm text-muted-foreground">{progressPercent}%</p>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(0, Math.min(100, progressPercent))}%` }} />
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {STAGES.map((stage, index) => {
                const done = completed || index < currentStageIndex;
                const active = !completed && !failed && index === currentStageIndex;
                return (
                  <div key={stage} className="rounded-md border bg-background p-3">
                    <p className="flex items-center gap-2 text-sm font-medium">
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      ) : (
                        <Circle className="h-4 w-4 text-muted-foreground" />
                      )}
                      {STAGE_LABELS[stage]}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Pages Crawled</p>
              <p className="mt-2 text-2xl font-semibold">{status?.progress?.pages_crawled ?? status?.results?.total_pages ?? 0}</p>
            </div>
            <div className="rounded-lg border bg-card p-4">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Records Extracted</p>
              <p className="mt-2 text-2xl font-semibold">{status?.progress?.records_extracted ?? status?.results?.total_records ?? 0}</p>
            </div>
          </section>

          {failed ? (
            <Alert
              variant="error"
              title="Smart Mining failed"
              description={status?.error_message ?? "Something went wrong during Smart Mining."}
            />
          ) : null}

          {completed ? (
            <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/30">
              <h2 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">Mining complete</h2>
              <p className="mt-1 text-sm text-emerald-800 dark:text-emerald-200">
                {status?.results?.total_records ?? status?.progress?.records_extracted ?? 0} records ready for review.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={() => navigate(`/records?source_id=${sourceId}`)}>View Records</Button>
                <Button variant="outline" onClick={() => navigate("/smart-mine")}>Start another</Button>
              </div>
            </section>
          ) : null}

          {(failed || statusQuery.isError) ? (
            <div>
              <Button variant="secondary" onClick={() => statusQuery.refetch()}>
                Retry status check
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
