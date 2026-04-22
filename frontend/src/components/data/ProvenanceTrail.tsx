import { Link } from "react-router-dom";

export interface ProvenanceNode {
  id: string;
  label: string;
  to: string;
}

interface ProvenanceTrailProps {
  nodes: ProvenanceNode[];
}

export function ProvenanceTrail({ nodes }: ProvenanceTrailProps) {
  return (
    <nav aria-label="Record provenance" className="rounded-lg border bg-card p-4">
      <p className="text-sm font-medium text-foreground">Provenance Chain</p>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        {nodes.map((node, idx) => (
          <div key={node.id} className="flex items-center gap-2">
            <Link className="rounded border px-2 py-1 text-primary hover:bg-muted/40" to={node.to}>
              {node.label}
            </Link>
            {idx < nodes.length - 1 ? <span className="text-muted-foreground">→</span> : null}
          </div>
        ))}
      </div>
    </nav>
  );
}
