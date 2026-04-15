import { Link } from "react-router-dom";
import type { ArtRecord } from "@/lib/api";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";

interface RecordTableRowProps {
  record: ArtRecord;
  selected: boolean;
  onToggleSelected: (id: string, checked: boolean) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export function RecordTableRow({
  record,
  selected,
  onToggleSelected,
  onApprove,
  onReject,
}: RecordTableRowProps) {
  return (
    <tr className="border-t hover:bg-gray-50">
      <td className="p-3 align-top">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => onToggleSelected(record.id, e.target.checked)}
          aria-label={`select-${record.id}`}
        />
      </td>
      <td className="p-3 align-top">
        <div className="font-medium text-sm text-gray-900">{record.title ?? "Untitled"}</div>
        {record.confidence_reasons?.length ? (
          <div className="text-[11px] text-gray-500 mt-1 line-clamp-2">
            {record.confidence_reasons.join(" · ")}
          </div>
        ) : (
          <div className="text-[11px] text-gray-400 mt-1">No confidence reasons</div>
        )}
      </td>
      <td className="p-3 align-top"><RecordTypeBadge type={record.record_type} /></td>
      <td className="p-3 align-top">
        <ConfidenceBadge
          band={record.confidence_band as "HIGH" | "MEDIUM" | "LOW"}
          score={record.confidence_score}
        />
      </td>
      <td className="p-3 align-top text-sm text-gray-600 max-w-[200px] truncate" title={record.source_id}>
        {record.source_id}
      </td>
      <td className="p-3 align-top">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onApprove(record.id)}
            className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
          >
            ✓
          </button>
          <button
            onClick={() => onReject(record.id)}
            className="px-2 py-1 text-xs border border-red-300 text-red-600 rounded hover:bg-red-50"
          >
            ✕
          </button>
          <Link
            to={`/records/${record.id}`}
            className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-100"
          >
            Edit
          </Link>
        </div>
      </td>
    </tr>
  );
}
