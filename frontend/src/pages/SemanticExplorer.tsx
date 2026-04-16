import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { relatedArtists, semanticArtistSearch } from "@/lib/api";
import { Button, Input, Spinner } from "@/components/ui";

export function SemanticExplorer() {
  const [query, setQuery] = useState("abstract expressionism");
  const [selectedArtist, setSelectedArtist] = useState<string | null>(null);

  const searchQuery = useQuery({
    queryKey: ["semantic-artists", query],
    queryFn: () => semanticArtistSearch(query),
    enabled: query.trim().length > 0,
  });

  const relatedQuery = useQuery({
    queryKey: ["related-artists", selectedArtist],
    queryFn: () => relatedArtists(selectedArtist as string),
    enabled: Boolean(selectedArtist),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">Semantic Explorer</h1>
      <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Semantic search artists…" />
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card rounded border p-3">
          <h2 className="font-semibold mb-2">Results</h2>
          <div className="space-y-2">
            {searchQuery.data?.items.map((item) => (
              <Button key={item.id} variant="secondary" className="w-full !justify-start h-auto py-2" onClick={() => setSelectedArtist(item.id)}>
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-muted-foreground">Semantic score: {item.semantic_score.toFixed(3)}</div>
              </Button>
            ))}
          </div>
        </div>
        <div className="bg-card rounded border p-3">
          <h2 className="font-semibold mb-2">Related Artists</h2>
          <div className="space-y-2">
            {relatedQuery.isLoading && <Spinner label="Loading related artists" />}
            {relatedQuery.data?.items.map((item) => (
              <div key={item.id} className="border rounded p-2">
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-muted-foreground">Similarity: {item.score.toFixed(3)}</div>
              </div>
            ))}
            {!selectedArtist && <div className="text-sm text-muted-foreground">Select a result to explore relationships.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
