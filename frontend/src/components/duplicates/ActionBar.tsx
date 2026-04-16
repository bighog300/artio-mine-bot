import { Check, SkipForward, Undo, X } from "lucide-react";

interface ActionBarProps {
  onMerge: () => void;
  onDismiss: () => void;
  onSkip: () => void;
  canUndo?: boolean;
  onUndo?: () => void;
  mergeDisabled?: boolean;
}

export function ActionBar({
  onMerge,
  onDismiss,
  onSkip,
  canUndo = false,
  onUndo,
  mergeDisabled = false,
}: ActionBarProps) {
  return (
    <footer className="bg-white border-t px-6 py-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={onMerge}
            disabled={mergeDisabled}
            className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Merge records (M)"
          >
            <Check className="h-5 w-5" />
            Merge Records
          </button>

          <button
            onClick={onDismiss}
            className="px-6 py-2.5 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium flex items-center gap-2"
            title="Not a duplicate (D)"
          >
            <X className="h-5 w-5" />
            Not Duplicate
          </button>

          <button
            onClick={onSkip}
            className="px-6 py-2.5 border border-gray-300 hover:bg-gray-50 rounded-lg font-medium flex items-center gap-2"
            title="Skip for now (S)"
          >
            <SkipForward className="h-5 w-5" />
            Skip
          </button>
        </div>

        {canUndo && onUndo && (
          <button
            onClick={onUndo}
            className="px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg text-sm flex items-center gap-2"
            type="button"
          >
            <Undo className="h-4 w-4" />
            Undo Last Action
          </button>
        )}
      </div>

      <div className="text-xs text-gray-500 mt-3 flex gap-4 flex-wrap">
        <span>
          <kbd className="px-2 py-1 bg-gray-100 rounded">M</kbd> Merge
        </span>
        <span>
          <kbd className="px-2 py-1 bg-gray-100 rounded">D</kbd> Dismiss
        </span>
        <span>
          <kbd className="px-2 py-1 bg-gray-100 rounded">S</kbd> Skip
        </span>
        <span>
          <kbd className="px-2 py-1 bg-gray-100 rounded">N</kbd> Next
        </span>
        <span>
          <kbd className="px-2 py-1 bg-gray-100 rounded">P</kbd> Previous
        </span>
      </div>
    </footer>
  );
}
