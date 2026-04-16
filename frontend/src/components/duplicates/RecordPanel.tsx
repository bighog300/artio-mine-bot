import type { ArtRecord } from "@/lib/api";

interface RecordPanelProps {
  record: ArtRecord;
  label: string;
  highlights?: string[];
}

const FIELD_CONFIG: Array<{ key: keyof ArtRecord; label: string }> = [
  { key: "title", label: "Name" },
  { key: "record_type", label: "Type" },
  { key: "nationality", label: "Nationality" },
  { key: "birth_year", label: "Birth Year" },
  { key: "city", label: "City" },
  { key: "country", label: "Country" },
  { key: "bio", label: "Biography" },
  { key: "website_url", label: "Website" },
  { key: "email", label: "Email" },
  { key: "source_url", label: "Source URL" },
];

function formatFieldValue(value: ArtRecord[keyof ArtRecord]): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  return String(value);
}

export function RecordPanel({ record, label, highlights = [] }: RecordPanelProps) {
  const imageUrl = record.primary_image_url ?? record.avatar_url ?? null;

  return (
    <article className="bg-white border rounded-lg p-4 h-full">
      <div className="flex items-center justify-between mb-4 gap-2">
        <h3 className="font-semibold text-lg">{label}</h3>
        <span className="text-xs text-gray-500 font-mono break-all">{record.id}</span>
      </div>

      {imageUrl && (
        <div className="mb-4">
          <img src={imageUrl} alt={record.title ?? "Record image"} className="w-full h-48 object-cover rounded" />
        </div>
      )}

      <div className="space-y-3">
        {FIELD_CONFIG.map(({ key, label: fieldLabel }) => {
          const value = record[key];
          if (value === null || value === undefined || value === "") {
            return null;
          }

          const isHighlighted = highlights.includes(String(key));
          const formattedValue = formatFieldValue(value);

          return (
            <div key={String(key)} className={isHighlighted ? "bg-yellow-50 p-2 rounded border border-yellow-200" : ""}>
              <div className="text-xs text-gray-500 font-medium">{fieldLabel}</div>
              <div className="text-sm mt-1 break-words">
                {key === "bio" && formattedValue.length > 240
                  ? `${formattedValue.slice(0, 240)}…`
                  : formattedValue}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t text-xs text-gray-500 space-y-1">
        <div>Source ID: {record.source_id}</div>
        <div>Created: {new Date(record.created_at).toLocaleDateString()}</div>
      </div>
    </article>
  );
}
