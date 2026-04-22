import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { type SourceVariant } from "@/api/entities";
import { cn } from "@/lib/utils";

interface SourceVariantCardProps {
  variant: SourceVariant;
  canonicalValues: Record<string, string>;
}

export function SourceVariantCard({ variant, canonicalValues }: SourceVariantCardProps) {
  const [expanded, setExpanded] = useState(false);

  const entries = useMemo(() => Object.entries(variant.values ?? {}), [variant.values]);

  return (
    <div className="rounded-lg border bg-card">
      <button className="flex w-full items-center justify-between gap-2 p-3 text-left" onClick={() => setExpanded((v) => !v)}>
        <div>
          <p className="font-medium">{variant.source_name}</p>
          <p className="text-xs text-muted-foreground">{entries.length} extracted fields</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-40"><ConfidenceBar score={variant.confidence} /></div>
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      {expanded ? (
        <div className="border-t p-3">
          <div className="grid gap-2 md:grid-cols-2">
            {entries.map(([field, value]) => {
              const canonical = canonicalValues[field] ?? "";
              const differs = canonical.trim() !== (value ?? "").trim();
              return (
                <div key={field} className={cn("rounded border p-2", differs ? "border-amber-300 bg-amber-50/50" : "")}> 
                  <p className="text-xs uppercase text-muted-foreground">{field}</p>
                  <p className="text-sm">{value || "—"}</p>
                  {differs ? <p className="mt-1 text-xs text-amber-800">Canonical: {canonical || "—"}</p> : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
