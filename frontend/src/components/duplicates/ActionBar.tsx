import { Check, SkipForward, Undo, X } from "lucide-react";
import { Button } from "@/components/ui";

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
          <Button
            onClick={onMerge}
            disabled={mergeDisabled}
            variant="primary"
            className="px-6"
            icon={<Check className="h-5 w-5" />}
            title="Merge records (M)"
          >
            Merge Records
          </Button>

          <Button
            onClick={onDismiss}
            variant="secondary"
            className="px-6"
            icon={<X className="h-5 w-5" />}
            title="Not a duplicate (D)"
          >
            Not Duplicate
          </Button>

          <Button
            onClick={onSkip}
            variant="ghost"
            className="px-6 border border-gray-300"
            icon={<SkipForward className="h-5 w-5" />}
            title="Skip for now (S)"
          >
            Skip
          </Button>
        </div>

        {canUndo && onUndo && (
          <Button
            onClick={onUndo}
            variant="ghost"
            size="sm"
            className="border border-gray-300"
            icon={<Undo className="h-4 w-4" />}
          >
            Undo Last Action
          </Button>
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
