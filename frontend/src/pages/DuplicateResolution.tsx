import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { decideDuplicate, getDuplicateReviews } from "@/lib/api";

export function DuplicateResolution() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["duplicate-reviews"],
    queryFn: () => getDuplicateReviews("pending"),
    retry: false,
  });

  const decideMutation = useMutation({
    mutationFn: decideDuplicate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["duplicate-reviews"] }),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Duplicate Resolution</h1>
      <div className="bg-white rounded border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-3 text-left">Pair</th>
              <th className="p-3 text-left">Similarity</th>
              <th className="p-3 text-left">Reasons</th>
              <th className="p-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={4} className="p-4 text-gray-500">Loading…</td></tr>}
            {data?.items.map((item) => (
              <tr key={item.id} className="border-t">
                <td className="p-3">{item.left_name} ↔ {item.right_name}</td>
                <td className="p-3">{(item.similarity_score * 100).toFixed(1)}%</td>
                <td className="p-3 text-gray-600">{item.reason}</td>
                <td className="p-3 space-x-2">
                  <button className="px-2 py-1 bg-green-600 text-white rounded" onClick={() => decideMutation.mutate({ left_id: item.left_id, right_id: item.right_id, decision: "merge", primary_id: item.left_id })}>Merge</button>
                  <button className="px-2 py-1 border rounded" onClick={() => decideMutation.mutate({ left_id: item.left_id, right_id: item.right_id, decision: "ignore" })}>Ignore</button>
                  <button className="px-2 py-1 border rounded" onClick={() => decideMutation.mutate({ left_id: item.left_id, right_id: item.right_id, decision: "not_duplicate" })}>Not duplicate</button>
                </td>
              </tr>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && <tr><td colSpan={4} className="p-4 text-gray-500">No candidates.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
