import { Link } from "react-router-dom";
import { type EntityRelationship } from "@/api/entities";

interface RelationshipListProps {
  items: EntityRelationship[];
}

export function RelationshipList({ items }: RelationshipListProps) {
  if (!items.length) {
    return <div className="rounded border bg-card p-4 text-sm text-muted-foreground">No relationships available for this entity yet.</div>;
  }

  const groupedItems = items
    .slice()
    .sort((a, b) => {
      const importanceDiff = (b.importance ?? 0) - (a.importance ?? 0);
      if (importanceDiff !== 0) return importanceDiff;
      const confidenceDiff = (b.confidence ?? 0) - (a.confidence ?? 0);
      if (confidenceDiff !== 0) return confidenceDiff;
      return new Date(b.last_updated ?? 0).getTime() - new Date(a.last_updated ?? 0).getTime();
    })
    .reduce<Record<string, EntityRelationship[]>>((acc, item) => {
      const key = item.relationship_type || "other";
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});

  const totalCount = Object.values(groupedItems).reduce((sum, relationships) => sum + relationships.length, 0);

  return (
    <div className="space-y-3 rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">Showing {totalCount} relationships across {Object.keys(groupedItems).length} groups.</p>
      {Object.entries(groupedItems).map(([groupType, groupItems]) => (
        <section key={groupType} className="space-y-2">
          <h3 className="text-sm font-semibold capitalize">{groupType} ({groupItems.length})</h3>
          <ul className="space-y-2">
            {groupItems.map((item) => (
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
        </section>
      ))}
    </div>
  );
}
