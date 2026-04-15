import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReviewArtist, resolveReviewConflict, rerunReviewArtist, searchReviewArtists } from "@/lib/api";

export function AdminReview() {
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const artistsQuery = useQuery({
    queryKey: ["review-artists", query],
    queryFn: () => searchReviewArtists({ has_conflicts: query ? undefined : true }),
  });

  const filtered = useMemo(
    () =>
      (artistsQuery.data?.items ?? []).filter((artist) =>
        (artist.title || "").toLowerCase().includes(query.toLowerCase())
      ),
    [artistsQuery.data?.items, query]
  );

  const activeId = selectedId ?? filtered[0]?.id;

  const artistDetail = useQuery({
    queryKey: ["review-artist", activeId],
    queryFn: () => getReviewArtist(activeId as string),
    enabled: Boolean(activeId),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ field, value }: { field: string; value: string }) =>
      resolveReviewConflict(activeId as string, field, value),
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
          <input
            placeholder="Search artists..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
          <div className="space-y-2 max-h-[620px] overflow-auto">
            {filtered.map((artist) => (
              <button
                key={artist.id}
                onClick={() => setSelectedId(artist.id)}
                className={`w-full text-left border rounded p-2 ${activeId === artist.id ? "border-blue-500 bg-blue-50" : ""}`}
              >
                <div className="font-medium">{artist.title}</div>
                <div className="text-xs text-gray-500">
                  Completeness: {artist.completeness_score} · Missing: {artist.missing_fields.length}
                </div>
              </button>
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
                <button
                  onClick={() => rerunMutation.mutate()}
                  className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded"
                >
                  Trigger rerun
                </button>
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
                          <button
                            key={`${field}-${opt.value}`}
                            onClick={() => resolveMutation.mutate({ field, value: opt.value })}
                            className="w-full text-left px-2 py-1.5 border rounded text-sm hover:bg-gray-50"
                          >
                            {opt.value}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {Object.keys(artistDetail.data.conflicts).length === 0 && (
                    <div className="text-sm text-gray-500">No conflicts pending.</div>
                  )}
                </div>
              </section>

              <section>
                <h3 className="font-medium mb-2">Related data</h3>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  {(["exhibitions", "articles", "press"] as const).map((key) => (
                    <div key={key} className="border rounded p-2">
                      <div className="font-medium capitalize">{key}</div>
                      <div className="text-gray-600 mt-1">{artistDetail.data.related?.[key]?.length ?? 0} items</div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
