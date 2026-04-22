import { Link } from "react-router-dom";
import { type EntityRelationship } from "@/api/entities";

interface RelationshipListProps {
  items: EntityRelationship[];
}

export function RelationshipList({ items }: RelationshipListProps) {
  if (!items.length) {
    return <div className="rounded border bg-card p-4 text-sm text-muted-foreground">No related entities yet.</div>;
  }

  return (
    <ul className="space-y-2 rounded-lg border bg-card p-4">
      {items.map((item) => (
        <li key={`${item.relationship_type}-${item.id}`} className="flex items-center justify-between rounded border p-2">
          <div>
            <p className="font-medium">{item.name}</p>
            <p className="text-xs text-muted-foreground">{item.relationship_type} · {item.type}</p>
          </div>
          <div className="flex items-center gap-3">
            {typeof item.count === "number" ? <span className="text-xs text-muted-foreground">{item.count}</span> : null}
            <Link className="text-sm text-primary underline" to={`/entities/${item.id}`}>View</Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
