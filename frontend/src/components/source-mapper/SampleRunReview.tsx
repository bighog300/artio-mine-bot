import type { MappingSampleRunResultResponse } from "@/lib/api";
import { SAMPLE_RUN_REVIEW_STATUSES, type SampleRunReviewStatus } from "@/components/source-mapper/constants";
import { useState } from "react";

interface Props {
  sampleRun?: MappingSampleRunResultResponse;
  onStart: () => void;
  loading: boolean;
  disabled?: boolean;
  disabledReason?: string | null;
  onModerateResult: (resultId: string, update: { review_status?: string; review_notes?: string }) => void;
}

export function SampleRunReview({ sampleRun, onStart, loading, disabled, disabledReason, onModerateResult }: Props) {
  const [savedNoteResultId, setSavedNoteResultId] = useState<string | null>(null);
  const reviewLabel: Record<SampleRunReviewStatus, string> = {
    approved: "Approve",
    needs_review: "Needs review",
    rejected: "Reject",
  };

  return (
    <section className="rounded border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Sample Extraction Review</h2>
        <button
          className="px-2 py-1 rounded bg-foreground text-white text-xs disabled:opacity-60"
          onClick={onStart}
          disabled={loading || disabled}
          title={disabledReason ?? undefined}
        >
          {loading ? "Running..." : "Run sample extraction"}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">Use sample extraction to validate approved rows before publishing. Notes autosave when focus leaves the notes field.</p>
      {disabledReason ? <p className="text-xs text-muted-foreground">{disabledReason}</p> : null}
      {!sampleRun ? <p className="text-sm text-muted-foreground">No sample run yet.</p> : (
        <>
          <p className="text-xs text-muted-foreground">Run {sampleRun.sample_run_id} · {sampleRun.status}</p>
          <ul className="space-y-1 text-xs">
            {sampleRun.items.slice(0, 5).map((item) => (
              <li key={item.id} className="border rounded p-2">
                <div className="flex items-center justify-between gap-2">
                  <div>Status: {item.review_status}</div>
                  <div className="flex gap-1">
                    {SAMPLE_RUN_REVIEW_STATUSES.map((status) => (
                      <button key={status} className="px-2 py-1 border rounded" onClick={() => onModerateResult(item.id, { review_status: status })}>
                        {reviewLabel[status]}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  className="mt-2 w-full rounded border px-2 py-1 text-xs"
                  rows={2}
                  defaultValue={item.review_notes ?? ""}
                  placeholder="Optional moderation notes"
                  onBlur={(e) => {
                    onModerateResult(item.id, { review_notes: e.target.value });
                    setSavedNoteResultId(item.id);
                  }}
                />
                {savedNoteResultId === item.id ? <p className="text-[11px] text-emerald-700 mt-1">Notes saved.</p> : null}
                <pre className="bg-muted/40 rounded p-2 mt-1 overflow-auto">{JSON.stringify(item.record_preview, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
