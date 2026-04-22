import { Link } from "react-router-dom";
import { AlertCircle, ArrowRight, ShieldCheck, TriangleAlert } from "lucide-react";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { Badge, Button, Skeleton } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { ControlCenterAction } from "@/features/control-center/types";

interface PrioritizedActionsPanelProps {
  isLoading: boolean;
  isError?: boolean;
  onRetry?: () => void;
  actions: ControlCenterAction[];
}

const severityStyles: Record<ControlCenterAction["severity"], { badge: "error" | "warning" | "info" | "default"; card: string }> = {
  critical: {
    badge: "error",
    card: "border-red-300 bg-red-50/40 dark:border-red-900 dark:bg-red-950/20",
  },
  high: {
    badge: "warning",
    card: "border-amber-300 bg-amber-50/30 dark:border-amber-900 dark:bg-amber-950/10",
  },
  medium: {
    badge: "info",
    card: "border-blue-300 bg-blue-50/20 dark:border-blue-900 dark:bg-blue-950/10",
  },
  low: {
    badge: "default",
    card: "border-border bg-card",
  },
};

function formatConfidence(confidence: number): number {
  return Math.round(confidence * 100);
}

export function PrioritizedActionsPanel({ isLoading, isError = false, onRetry, actions }: PrioritizedActionsPanelProps) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm lg:p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Prioritized actions</h2>
          <p className="text-xs text-muted-foreground">Handle these first to keep mining health stable.</p>
        </div>
        <TriangleAlert className="h-4 w-4 text-amber-500" />
      </div>

      <div className="space-y-3" role="status" aria-live="polite">
        {isLoading && Array.from({ length: 4 }).map((_, idx) => <Skeleton key={idx} className="h-28 rounded-md" />)}

        {!isLoading && isError ? (
          <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
            <div className="mb-3 flex items-center gap-2 font-medium">
              <AlertCircle className="h-4 w-4" />
              Unable to load prioritized actions.
            </div>
            {onRetry ? (
              <Button variant="secondary" size="sm" onClick={onRetry}>
                Retry
              </Button>
            ) : null}
          </div>
        ) : null}

        {!isLoading && !isError && actions.length === 0 ? (
          <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
            System healthy — no actions required
          </div>
        ) : null}

        {!isLoading && !isError && actions.map((action, idx) => {
          const style = severityStyles[action.severity];
          return (
            <article
              key={action.id}
              className={cn(
                "rounded-md border p-3 transition-colors",
                style.card,
                idx === 0 && "ring-1 ring-offset-1 ring-foreground/15",
              )}
            >
              <div className="mb-2 flex items-start justify-between gap-3">
                <div>
                  <p className={cn("text-sm font-semibold text-foreground", idx === 0 && "text-base")}>{action.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{action.impactSummary}</p>
                </div>
                <Badge variant={style.badge}>{action.severity.toUpperCase()}</Badge>
              </div>

              <p className="mb-2 text-xs text-muted-foreground">{action.description}</p>

              {typeof action.confidence === "number" ? (
                <div className="mb-3">
                  <p className="mb-1 text-xs text-muted-foreground">Confidence</p>
                  <ConfidenceBar score={formatConfidence(action.confidence)} />
                </div>
              ) : null}

              <Link
                to={action.cta.to}
                className="inline-flex min-h-[36px] items-center gap-2 rounded-md bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-secondary/80"
              >
                {action.cta.label}
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
