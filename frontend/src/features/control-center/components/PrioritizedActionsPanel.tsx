import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, TriangleAlert } from "lucide-react";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Skeleton } from "@/components/ui";
import { cn } from "@/lib/utils";

interface PrioritizedAction {
  id: string;
  title: string;
  description: string;
  status: "ready" | "attention";
  confidence: number;
  href: string;
}

interface PrioritizedActionsPanelProps {
  isLoading: boolean;
  actions: PrioritizedAction[];
}

export function PrioritizedActionsPanel({ isLoading, actions }: PrioritizedActionsPanelProps) {
  return (
    <section className="rounded-lg border bg-card p-4 lg:p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Prioritized actions</h2>
          <p className="text-xs text-muted-foreground">Handle these first to keep mining health stable.</p>
        </div>
        <TriangleAlert className="h-4 w-4 text-amber-500" />
      </div>

      <div className="space-y-3" role="status" aria-live="polite">
        {isLoading
          ? Array.from({ length: 3 }).map((_, idx) => <Skeleton key={idx} className="h-20 rounded-md" />)
          : actions.map((action) => (
              <div key={action.id} className="rounded-md border p-3">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{action.title}</p>
                    <p className="text-xs text-muted-foreground">{action.description}</p>
                  </div>
                  <StatusBadge status={action.status === "attention" ? "failed" : "approved"} />
                </div>
                <ConfidenceBar score={action.confidence} />
                <div className="mt-3">
                  <Link
                    to={action.href}
                    className={cn(
                      "inline-flex min-h-[36px] items-center gap-2 rounded-md bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-secondary/80",
                    )}
                  >
                    Open
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
      </div>

      {!isLoading && actions.every((action) => action.status === "ready") ? (
        <div className="mt-4 flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300">
          <ShieldCheck className="h-4 w-4" />
          No critical actions pending.
        </div>
      ) : null}
    </section>
  );
}
