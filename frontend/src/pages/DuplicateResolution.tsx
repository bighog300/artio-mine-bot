import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  dismissDuplicate,
  getDuplicatePair,
  getDuplicates,
  mergeDuplicates,
  type DuplicatePairWithRecords,
} from "@/lib/api";
import { ActionBar } from "@/components/duplicates/ActionBar";
import { DuplicateHeader } from "@/components/duplicates/DuplicateHeader";
import { MergeControlPanel } from "@/components/duplicates/MergeControlPanel";
import { RecordPanel } from "@/components/duplicates/RecordPanel";

export function DuplicateResolution() {
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [mergeStrategy, setMergeStrategy] = useState<Record<string, "a" | "b" | "both">>({});
  const [keepRecordId, setKeepRecordId] = useState<"a" | "b">("a");

  const { data: pairsData, isLoading: isPairsLoading } = useQuery({
    queryKey: ["duplicates", "pending"],
    queryFn: () => getDuplicates({ status: "pending", limit: 100 }),
  });

  const pairs = pairsData?.items ?? [];
  const safeIndex = pairs.length === 0 ? 0 : Math.min(currentIndex, pairs.length - 1);
  const currentPair = pairs[safeIndex];

  const {
    data: pairDetails,
    isLoading: isPairLoading,
    isError: isPairError,
  } = useQuery<DuplicatePairWithRecords>({
    queryKey: ["duplicate-pair", currentPair?.id],
    queryFn: () => getDuplicatePair(currentPair!.id),
    enabled: Boolean(currentPair),
  });

  useEffect(() => {
    if (!pairDetails) {
      return;
    }

    const initialStrategy: Record<string, "a" | "b" | "both"> = {};
    pairDetails.pair.conflicting_fields.forEach((conflict) => {
      initialStrategy[conflict.field] = "a";
    });
    setMergeStrategy(initialStrategy);
    setKeepRecordId("a");
  }, [pairDetails?.pair.id]);

  const moveToPrevious = () => {
    setCurrentIndex((previous) => Math.max(0, previous - 1));
  };

  const moveToNext = () => {
    setCurrentIndex((previous) => Math.min(Math.max(pairs.length - 1, 0), previous + 1));
  };

  const mergeMutation = useMutation({
    mutationFn: async () => {
      if (!currentPair || !pairDetails) {
        return null;
      }

      const keepId = keepRecordId === "a" ? pairDetails.record_a.id : pairDetails.record_b.id;
      return mergeDuplicates(currentPair.id, keepId, mergeStrategy);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
      moveToNext();
    },
  });

  const dismissMutation = useMutation({
    mutationFn: async () => {
      if (!currentPair) {
        return null;
      }
      return dismissDuplicate(currentPair.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
      moveToNext();
    },
  });

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === "n") {
        moveToNext();
      } else if (key === "p") {
        moveToPrevious();
      } else if (key === "s") {
        moveToNext();
      } else if (key === "m" && !mergeMutation.isPending) {
        mergeMutation.mutate();
      } else if (key === "d" && !dismissMutation.isPending) {
        dismissMutation.mutate();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [mergeMutation, dismissMutation, pairs.length]);

  const conflictingFields = useMemo(
    () => (pairDetails?.pair.conflicting_fields ?? []).map((conflict) => conflict.field),
    [pairDetails?.pair.conflicting_fields]
  );

  if (!isPairsLoading && pairs.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-muted/40">
        <div className="text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-foreground mb-2">No Duplicates Found</h2>
          <p className="text-muted-foreground">All duplicate pairs have been resolved.</p>
        </div>
      </div>
    );
  }

  if (isPairsLoading || isPairLoading || !pairDetails) {
    return (
      <div className="h-screen flex items-center justify-center" role="status" aria-live="polite" aria-busy="true">
        <div className="text-muted-foreground">Loading duplicate pair…</div>
      </div>
    );
  }

  if (isPairError) {
    return (
      <div className="h-screen flex items-center justify-center" role="alert">
        <div className="text-red-700">Unable to load duplicate details right now.</div>
      </div>
    );
  }

  const { pair, record_a: recordA, record_b: recordB } = pairDetails;

  return (
    <div className="h-screen flex flex-col bg-muted/40">
      <h1 className="sr-only">Duplicate Resolution</h1>
      <DuplicateHeader
        total={pairs.length}
        current={safeIndex}
        similarityScore={pair.similarity_score}
        onPrevious={moveToPrevious}
        onNext={moveToNext}
      />

      <section className="flex-1 overflow-auto" aria-label="Duplicate record comparison">
        <div className="max-w-7xl mx-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <input
                  type="radio"
                  name="keep-record"
                  id="keep-a"
                  checked={keepRecordId === "a"}
                  onChange={() => setKeepRecordId("a")}
                  className="w-4 h-4"
                />
                <label htmlFor="keep-a" className="text-sm font-medium cursor-pointer">
                  Keep this record
                </label>
              </div>
              <RecordPanel record={recordA} label="Record A" highlights={conflictingFields} />
            </div>

            <div>
              <div className="mb-2 flex items-center gap-2">
                <input
                  type="radio"
                  name="keep-record"
                  id="keep-b"
                  checked={keepRecordId === "b"}
                  onChange={() => setKeepRecordId("b")}
                  className="w-4 h-4"
                />
                <label htmlFor="keep-b" className="text-sm font-medium cursor-pointer">
                  Keep this record
                </label>
              </div>
              <RecordPanel record={recordB} label="Record B" highlights={conflictingFields} />
            </div>
          </div>

          <MergeControlPanel
            conflicts={pair.conflicting_fields}
            strategy={mergeStrategy}
            onChange={(field, choice) => setMergeStrategy((previous) => ({ ...previous, [field]: choice }))}
          />
        </div>
      </section>

      <ActionBar
        onMerge={() => mergeMutation.mutate()}
        onDismiss={() => dismissMutation.mutate()}
        onSkip={moveToNext}
        mergeDisabled={mergeMutation.isPending || dismissMutation.isPending}
      />
    </div>
  );
}
