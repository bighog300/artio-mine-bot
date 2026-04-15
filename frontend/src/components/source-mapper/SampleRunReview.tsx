import type { MappingSampleRunResultResponse } from "@/lib/api";

interface Props {
  sampleRun?: MappingSampleRunResultResponse;
  onStart: () => void;
  loading: boolean;
}

export function SampleRunReview({ sampleRun, onStart, loading }: Props) {
  return (
    <section className="rounded border bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Sample Extraction Review</h2>
        <button className="px-2 py-1 rounded bg-slate-800 text-white text-xs disabled:opacity-60" onClick={onStart} disabled={loading}>
          {loading ? "Running..." : "Run sample extraction"}
        </button>
      </div>
      {!sampleRun ? <p className="text-sm text-gray-500">No sample run yet.</p> : (
        <>
          <p className="text-xs text-gray-500">Run {sampleRun.sample_run_id} · {sampleRun.status}</p>
          <ul className="space-y-1 text-xs">
            {sampleRun.items.slice(0, 5).map((item) => (
              <li key={item.id} className="border rounded p-2">
                <div>Status: {item.review_status}</div>
                <pre className="bg-slate-50 rounded p-2 mt-1 overflow-auto">{JSON.stringify(item.record_preview, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
