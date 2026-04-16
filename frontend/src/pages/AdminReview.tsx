import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReviewArtist, resolveReviewConflict, rerunReviewArtist, searchReviewArtists } from "@/lib/api";
import { Button, Input } from "@/components/ui";

export function AdminReview() {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const artistsQuery = useQuery({
    queryKey: ["review-artists", query],
    queryFn: () => searchReviewArtists({ has_conflicts: query ? undefined : true }),
  });

  const filtered = useMemo(
    () => (artistsQuery.data?.items ?? []).filter((artist) => (artist.title || "").toLowerCase().includes(query.toLowerCase())),
    [artistsQuery.data?.items, query],
  );

  const activeId = selectedId ?? filtered[0]?.id;

  const artistDetail = useQuery({
    queryKey: ["review-artist", activeId],
    queryFn: () => getReviewArtist(activeId as string),
    enabled: Boolean(activeId),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ field, value }: { field: string; value: string }) => resolveReviewConflict(activeId as string, field, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["review-artist", activeId] }),
  });

  const rerunMutation = useMutation({
    mutationFn: () => rerunReviewArtist(activeId as string),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["review-artist", activeId] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Admin Review</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded border p-3 space-y-3">
          <Input placeholder="Search artists..." value={query} onChange={(e) => setQuery(e.target.value)} />
          <div className="space-y-2 max-h-[620px] overflow-auto">
            {filtered.map((artist) => (
              <Button
                key={artist.id}
                onClick={() => setSelectedId(artist.id)}
                variant="secondary"
                className={`w-full !justify-start h-auto py-2 ${activeId === artist.id ? "ring-2 ring-blue-500" : ""}`}
              >
                <span>
                  <span className="font-medium block">{artist.title}</span>
                  <span className="text-xs text-gray-500">Completeness: {artist.completeness_score} · Missing: {artist.missing_fields.length}</span>
                </span>
              </Button>
            ))}
          </div>
        </div>

        <div className="col-span-2 bg-white rounded border p-4 space-y-4">
          {!artistDetail.data && <div className="text-gray-500 text-sm">Select an artist to review.</div>}
          {artistDetail.data && (
            <>
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{artistDetail.data.title}</h2>
                  <p className="text-sm text-gray-500">Completeness: {artistDetail.data.completeness_score}</p>
                </div>
                <Button onClick={() => rerunMutation.mutate()} loading={rerunMutation.isPending}>Trigger rerun</Button>
              </div>

              <section>
                <h3 className="font-medium mb-1">Missing fields</h3>
                <div className="text-sm text-gray-700">{artistDetail.data.missing_fields.join(", ") || "None"}</div>
              </section>

              <section>
                <h3 className="font-medium mb-2">Conflicts</h3>
                <div className="space-y-3">
                  {Object.entries(artistDetail.data.conflicts).map(([field, options]) => (
                    <div key={field} className="border rounded p-3">
                      <div className="font-medium text-sm mb-2">{field}</div>
                      <div className="space-y-2">
                        {options.map((opt) => (
                          <Button
                            key={`${field}-${opt.value}`}
                            onClick={() => resolveMutation.mutate({ field, value: opt.value })}
                            className="w-full !justify-start"
                            variant="secondary"
                            size="sm"
                          >
                            {opt.value}
                          </Button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.keys(artistDetail.data.conflicts).length === 0 && <div className="text-sm text-gray-500">No conflicts pending.</div>}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
