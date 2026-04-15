import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { relatedArtists, semanticArtistSearch } from "@/lib/api";

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
      <h1 className="text-2xl font-bold text-gray-900">Semantic Explorer</h1>
      <input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full border rounded px-3 py-2" placeholder="Semantic search artists…" />
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded border p-3">
          <h2 className="font-semibold mb-2">Results</h2>
          <div className="space-y-2">
            {searchQuery.data?.items.map((item) => (
              <button key={item.id} className="w-full text-left border rounded p-2 hover:bg-gray-50" onClick={() => setSelectedArtist(item.id)}>
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-gray-500">Semantic score: {item.semantic_score.toFixed(3)}</div>
              </button>
            ))}
          </div>
        </div>
        <div className="bg-white rounded border p-3">
          <h2 className="font-semibold mb-2">Related Artists</h2>
          <div className="space-y-2">
            {relatedQuery.data?.items.map((item) => (
              <div key={item.id} className="border rounded p-2">
                <div className="font-medium">{item.name}</div>
                <div className="text-xs text-gray-500">Similarity: {item.score.toFixed(3)}</div>
              </div>
            ))}
            {!selectedArtist && <div className="text-sm text-gray-500">Select a result to explore relationships.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
