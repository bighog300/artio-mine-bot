import { ChevronLeft, ChevronRight, HelpCircle } from "lucide-react";

interface DuplicateHeaderProps {
  total: number;
  current: number;
  similarityScore: number;
  onPrevious: () => void;
  onNext: () => void;
}

export function DuplicateHeader({
  total,
  current,
  similarityScore,
  onPrevious,
  onNext,
}: DuplicateHeaderProps) {
  const progress = total > 0 ? ((current + 1) / total) * 100 : 0;

  return (
    <header className="bg-white border-b px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-600">Reviewing {current + 1} of {total}</div>
          <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Similarity:</span>
          <span
            className={`font-bold ${
              similarityScore >= 90 ? "text-red-600" : similarityScore >= 75 ? "text-orange-600" : "text-yellow-600"
            }`}
          >
            {similarityScore.toFixed(0)}%
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onPrevious}
            disabled={current === 0}
            className="p-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Previous (P)"
            aria-label="Previous duplicate"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={onNext}
            disabled={current >= total - 1}
            className="p-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Next (N)"
            aria-label="Next duplicate"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
          <button
            className="p-2 border rounded hover:bg-gray-50"
            title="Keyboard shortcuts: N=Next, P=Previous, M=Merge, D=Dismiss, S=Skip"
            aria-label="Keyboard shortcuts"
            type="button"
          >
            <HelpCircle className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
