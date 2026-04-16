import type { MappingPageType } from "@/lib/api";

interface Props {
  pageTypes: MappingPageType[];
}

export function PageTypeSidebar({ pageTypes }: Props) {
  return (
    <section className="rounded border bg-card p-4">
      <h2 className="font-semibold mb-2">Detected page types</h2>
      {!pageTypes.length ? <p className="text-sm text-muted-foreground">No detected page types yet.</p> : (
        <ul className="space-y-2 text-sm">
          {pageTypes.map((item) => (
            <li key={item.id} className="rounded border p-2">
              <div className="font-medium">{item.label}</div>
              <div className="text-xs text-muted-foreground">{item.key}</div>
              <div className="text-xs">Samples: {item.sample_count} · Confidence: {Math.round(item.confidence_score * 100)}%</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
