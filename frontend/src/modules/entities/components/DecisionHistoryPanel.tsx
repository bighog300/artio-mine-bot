import { useMemo, useState } from "react";
import { type EntityDecisionHistoryItem } from "@/api/entities";
import { formatRelative } from "@/lib/utils";

interface DecisionHistoryPanelProps {
  items: EntityDecisionHistoryItem[];
}

function actionLabel(actionType: EntityDecisionHistoryItem["action_type"]) {
  if (actionType === "resolve") return "Resolved";
  if (actionType === "merge") return "Merged";
  return "Split";
}

function asDisplayValue(value?: string | null) {
  return value && value.trim().length > 0 ? value : "—";
}

export function DecisionHistoryPanel({ items }: DecisionHistoryPanelProps) {
  const [openById, setOpenById] = useState<Record<string, boolean>>({});
  const orderedItems = useMemo(
    () => [...items].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
    [items],
  );

  if (orderedItems.length === 0) {
    return (
      <div className="rounded border bg-card p-4 text-sm text-muted-foreground">
        No resolution, merge, or split actions have been recorded for this entity.
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-lg border bg-card p-4">
      {orderedItems.map((item) => {
        const isOpen = openById[item.id] ?? false;
        return (
          <article key={item.id} className="rounded border p-3">
            <button
              type="button"
              className="flex w-full flex-col text-left"
              onClick={() => setOpenById((current) => ({ ...current, [item.id]: !isOpen }))}
            >
              <span className="text-sm font-semibold">
                {item.field ? `${item.field} ${actionLabel(item.action_type).toLowerCase()}` : actionLabel(item.action_type)}
              </span>
              <span className="text-xs text-muted-foreground">{formatRelative(item.timestamp)}</span>
            </button>

            {isOpen ? (
              <div className="mt-3 space-y-1 text-sm">
                <p>
                  <span className="font-medium">Action:</span> {actionLabel(item.action_type)}
                </p>
                {item.field ? (
                  <p>
                    <span className="font-medium">Field:</span> {item.field}
                  </p>
                ) : null}
                <p>
                  <span className="font-medium">Value change:</span> {asDisplayValue(item.old_value)} {"->"} {asDisplayValue(item.new_value)}
                </p>
                <p>
                  <span className="font-medium">Source:</span> {asDisplayValue(item.source)}
                </p>
                <p>
                  <span className="font-medium">Operator:</span> {asDisplayValue(item.operator)}
                </p>
                <p>
                  <span className="font-medium">Timestamp:</span> {new Date(item.timestamp).toLocaleString()}
                </p>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
