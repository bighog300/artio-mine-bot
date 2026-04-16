import { useEffect, useState } from "react";

interface Props {
  open: boolean;
  draftId: string;
  creating: boolean;
  onClose: () => void;
  onCreate: (payload: { name: string; description?: string; include_statuses: string[] }) => void;
}

export function CreatePresetDialog({ open, draftId, creating, onClose, onCreate }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [approvedOnly, setApprovedOnly] = useState(true);

  useEffect(() => {
    if (open) {
      setName("");
      setDescription("");
      setApprovedOnly(true);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded border bg-white p-4 space-y-3">
        <h3 className="text-lg font-semibold">Save as Preset</h3>
        <p className="text-xs text-gray-500">Create a reusable snapshot from draft/version findings.</p>

        <label className="block text-sm space-y-1">
          <span className="font-medium">Preset Name</span>
          <input
            className="w-full rounded border px-2 py-1"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Approved Event Mapping"
            disabled={creating}
          />
        </label>

        <label className="block text-sm space-y-1">
          <span className="font-medium">Description (optional)</span>
          <textarea
            className="w-full rounded border px-2 py-1"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            disabled={creating}
          />
        </label>

        <div className="rounded border bg-slate-50 px-3 py-2 text-xs">Source draft/version: <strong>{draftId}</strong></div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={approvedOnly}
            onChange={(e) => setApprovedOnly(e.target.checked)}
            disabled={creating}
          />
          Include approved rows only
        </label>

        <div className="flex justify-end gap-2">
          <button className="px-3 py-1 border rounded" onClick={onClose} disabled={creating}>Cancel</button>
          <button
            className="px-3 py-1 rounded bg-slate-900 text-white disabled:opacity-60"
            onClick={() => onCreate({ name, description: description || undefined, include_statuses: approvedOnly ? ["approved"] : ["approved", "needs_review", "proposed", "changed_from_published"] })}
            disabled={creating || !name.trim()}
          >
            {creating ? "Saving..." : "Create Preset"}
          </button>
        </div>
      </div>
    </div>
  );
}
