import { useState } from "react";
import type { MappingPageType } from "@/lib/api";

interface Props {
  pageTypes: MappingPageType[];
  onAssignTargetType?: (pageTypeId: string, targetType: string) => void;
}

const TARGET_TYPES = ["artist", "venue", "event", "exhibition", "artwork", "organization"];

export function PageTypeSidebar({ pageTypes, onAssignTargetType }: Props) {
  const [pendingByPageType, setPendingByPageType] = useState<Record<string, string>>({});

  return (
    <section className="rounded border bg-card p-4">
      <h2 className="font-semibold mb-2">Detected page roles</h2>
      <p className="text-xs text-muted-foreground mb-3">Assign target record types per role to make mapping the runtime extraction contract.</p>
      {!pageTypes.length ? <p className="text-sm text-muted-foreground">No detected page types yet.</p> : (
        <ul className="space-y-2 text-sm">
          {pageTypes.map((item) => (
            <li key={item.id} className="rounded border p-2 space-y-2">
              <div className="font-medium">{item.label}</div>
              <div className="text-xs text-muted-foreground">{item.key}</div>
              <div className="text-xs">Samples: {item.sample_count} · Confidence: {Math.round(item.confidence_score * 100)}%</div>
              {onAssignTargetType && (
                <div className="flex gap-2 items-center">
                  <select
                    className="border rounded px-2 py-1 text-xs"
                    value={pendingByPageType[item.id] ?? "artist"}
                    onChange={(e) => setPendingByPageType((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    aria-label={`target-type-${item.id}`}
                  >
                    {TARGET_TYPES.map((targetType) => <option key={targetType} value={targetType}>{targetType}</option>)}
                  </select>
                  <button
                    className="border rounded px-2 py-1 text-xs"
                    onClick={() => onAssignTargetType(item.id, pendingByPageType[item.id] ?? "artist")}
                    type="button"
                  >
                    Assign target
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
