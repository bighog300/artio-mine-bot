import type { MiningStatus } from "@/lib/api";

interface PipelineProgressProps {
  sourceStatus: string;
  progress: MiningStatus["progress"];
  recordsDelta: number;
}

const orderedTypes = ["artist", "event", "exhibition", "venue", "artwork"] as const;

export function PipelineProgress({ sourceStatus, progress, recordsDelta }: PipelineProgressProps) {
  if (!progress) {
    return <div className="bg-white border rounded p-4 text-sm text-gray-500">Waiting for progress updates…</div>;
  }

  const crawledPercent = progress.pages_total_estimated > 0
    ? Math.min(100, Math.round((progress.pages_crawled / progress.pages_total_estimated) * 100))
    : 0;
  const extractedPercent = progress.pages_eligible_for_extraction > 0
    ? Math.min(100, Math.round((progress.pages_classified / progress.pages_eligible_for_extraction) * 100))
    : 0;

  const typeCounts = orderedTypes.map((type) => ({ type, count: progress.records_by_type?.[type] ?? 0 }));
  const totalTypeCount = typeCounts.reduce((acc, item) => acc + item.count, 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Pages Found" value={progress.pages_total_estimated} />
        <StatCard label="Pages Crawled" value={progress.pages_crawled} miniPercent={crawledPercent} />
        <StatCard label="Pages Extracted" value={progress.pages_classified} miniPercent={extractedPercent} />
        <StatCard label="Records" value={progress.records_extracted} delta={recordsDelta} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <PipelineStages sourceStatus={sourceStatus} progress={progress} />
        <RecordTypeBar typeCounts={typeCounts} total={totalTypeCount} />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  miniPercent,
  delta,
}: {
  label: string;
  value: number;
  miniPercent?: number;
  delta?: number;
}) {
  return (
    <div className="bg-white border rounded p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {typeof miniPercent === "number" && (
        <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
          <div className="h-full bg-blue-600" style={{ width: `${miniPercent}%` }} />
        </div>
      )}
      {delta !== undefined && delta > 0 && (
        <div className="text-xs text-green-600 mt-2">↑ {delta} in last refresh</div>
      )}
    </div>
  );
}

function PipelineStages({
  sourceStatus,
  progress,
}: {
  sourceStatus: string;
  progress: NonNullable<MiningStatus["progress"]>;
}) {
  const stages = [
    { key: "mapping", label: "Site mapping", meta: progress.pages_total_estimated > 0 ? "done" : "pending" },
    { key: "crawling", label: "Crawling", meta: `${progress.pages_crawled} / ${progress.pages_total_estimated} pages` },
    { key: "extracting", label: "Extracting", meta: `${progress.pages_classified} pages processed` },
    { key: "images", label: "Image collection", meta: `${progress.images_collected} images` },
  ];

  const normalize = (status: string) => {
    if (["queued", "pending", "mapping"].includes(status)) return "mapping";
    if (["running", "crawling"].includes(status)) return "crawling";
    if (["extracting"].includes(status)) return "extracting";
    if (["done"].includes(status)) return "images";
    return "mapping";
  };
  const activeStage = normalize(sourceStatus);
  const stageOrder = ["mapping", "crawling", "extracting", "images"];

  return (
    <div className="bg-white border rounded p-4">
      <h3 className="text-sm font-medium mb-3">Pipeline stages</h3>
      <div className="space-y-2">
        {stages.map((stage) => {
          const stageIdx = stageOrder.indexOf(stage.key);
          const activeIdx = stageOrder.indexOf(activeStage);
          const state = stageIdx < activeIdx ? "done" : stageIdx === activeIdx ? "active" : "pending";
          return (
            <div key={stage.key} className="flex items-start gap-2">
              <div
                className={`mt-1 h-2.5 w-2.5 rounded-full ${
                  state === "done"
                    ? "bg-green-500"
                    : state === "active"
                      ? "bg-blue-500"
                      : "bg-gray-300"
                }`}
              />
              <div>
                <div className="text-sm font-medium text-gray-800">{stage.label}</div>
                <div className="text-xs text-gray-500">{stage.meta}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RecordTypeBar({
  typeCounts,
  total,
}: {
  typeCounts: Array<{ type: string; count: number }>;
  total: number;
}) {
  if (total === 0) {
    return (
      <div className="bg-white border rounded p-4 text-sm text-gray-500">
        No records extracted yet.
      </div>
    );
  }

  const colors: Record<string, string> = {
    artist: "bg-purple-500",
    event: "bg-blue-500",
    exhibition: "bg-amber-500",
    venue: "bg-green-500",
    artwork: "bg-pink-500",
  };

  return (
    <div className="bg-white border rounded p-4">
      <h3 className="text-sm font-medium mb-3">Record type breakdown</h3>
      <div className="h-4 rounded overflow-hidden flex bg-gray-100">
        {typeCounts.map((item) => {
          if (item.count === 0) return null;
          const width = Math.max(2, Math.round((item.count / total) * 100));
          return (
            <div
              key={item.type}
              className={colors[item.type] ?? "bg-gray-400"}
              style={{ width: `${width}%` }}
              title={`${item.type}: ${item.count}`}
            />
          );
        })}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        {typeCounts.map((item) => (
          <div key={item.type} className="flex items-center justify-between text-gray-600">
            <span className="capitalize">{item.type}</span>
            <span>{item.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
