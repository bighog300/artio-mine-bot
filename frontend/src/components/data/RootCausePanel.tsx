import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { normalizeSeverity, severityBadgeClass, severityLabel, type SeverityLevel } from "@/lib/severity";

interface RootCausePanelProps {
  title?: string;
  items: string[];
  mappingLink?: string;
  ctaLabel?: string;
  severity?: SeverityLevel | string;
}

export function RootCausePanel({
  title = "This issue is likely caused by:",
  items,
  mappingLink,
  ctaLabel = "Fix Mapping",
  severity = "high",
}: RootCausePanelProps) {
  const topItems = items.filter((item) => item.trim().length > 0).slice(0, 3);

  if (!topItems.length) {
    return null;
  }

  const tone = normalizeSeverity(severity);

  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-orange-600" />
          <h2 className="text-base font-semibold">Root Cause</h2>
        </div>
        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${severityBadgeClass[tone]}`}>
          {severityLabel[tone]}
        </span>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        {topItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {mappingLink ? (
        <Link className="mt-3 inline-block text-sm font-medium text-primary underline" to={mappingLink}>
          → {ctaLabel}
        </Link>
      ) : null}
    </section>
  );
}
