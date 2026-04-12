import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { getRecord, updateRecord, approveRecord, rejectRecord, setPrimaryImage, type ArtRecord } from "@/lib/api";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TagInput } from "@/components/shared/TagInput";
import { ImageThumbnail } from "@/components/shared/ImageThumbnail";

export function RecordDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<ArtRecord>>({});

  const { data: record, isLoading } = useQuery({
    queryKey: ["record", id],
    queryFn: () => getRecord(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (record) setFormData(record);
  }, [record]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<ArtRecord>) => updateRecord(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["record", id] });
      setEditing(false);
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveRecord(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["record", id] }),
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectRecord(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["record", id] }),
  });

  const setPrimaryMutation = useMutation({
    mutationFn: (imageId: string) => setPrimaryImage(id!, imageId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["record", id] }),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!record) return <div className="p-6 text-red-500">Record not found</div>;

  const getField = (key: keyof ArtRecord) => formData[key] as string | null | undefined;
  const setField = (key: keyof ArtRecord, value: unknown) =>
    setFormData((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-sm text-gray-500 hover:text-gray-700">
          ← Back
        </button>
        <RecordTypeBadge type={record.record_type} />
        <StatusBadge status={record.status} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: fields */}
        <div className="col-span-2 bg-white border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">{record.title ?? "Untitled"}</h1>
            <div className="flex gap-2">
              <button
                onClick={() => editing ? updateMutation.mutate(formData) : setEditing(true)}
                className="px-3 py-1.5 border rounded text-sm hover:bg-gray-50"
              >
                {editing ? "Save" : "Edit"}
              </button>
              {editing && (
                <button onClick={() => setEditing(false)} className="px-3 py-1.5 text-sm text-gray-500">
                  Cancel
                </button>
              )}
            </div>
          </div>

          {renderFieldRow("Title", "title", getField, setField, editing)}
          {renderFieldRow("Description", "description", getField, setField, editing, true)}

          {record.record_type === "artist" && (
            <>
              {renderFieldRow("Bio", "bio", getField, setField, editing, true)}
              {renderFieldRow("Nationality", "nationality", getField, setField, editing)}
              {renderFieldRow("Website", "website_url", getField, setField, editing)}
              {editing && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mediums</label>
                  <TagInput
                    values={(formData["mediums"] as string[]) ?? []}
                    onChange={(v) => setField("mediums", v)}
                  />
                </div>
              )}
            </>
          )}

          {(record.record_type === "event" || record.record_type === "exhibition") && (
            <>
              {renderFieldRow("Venue", "venue_name", getField, setField, editing)}
              {renderFieldRow("Start Date", "start_date", getField, setField, editing)}
              {renderFieldRow("End Date", "end_date", getField, setField, editing)}
            </>
          )}

          {record.record_type === "venue" && (
            <>
              {renderFieldRow("Address", "address", getField, setField, editing)}
              {renderFieldRow("City", "city", getField, setField, editing)}
              {renderFieldRow("Country", "country", getField, setField, editing)}
            </>
          )}

          {/* Confidence */}
          <div className="border-t pt-3">
            <label className="block text-sm font-medium text-gray-700 mb-2">Confidence</label>
            <ConfidenceBar score={record.confidence_score} reasons={record.confidence_reasons} />
          </div>

          {/* Actions */}
          <div className="flex gap-2 border-t pt-3">
            <button
              onClick={() => approveMutation.mutate()}
              className="flex-1 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium"
            >
              Approve
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              className="flex-1 py-2 border border-red-300 text-red-600 rounded hover:bg-red-50 text-sm"
            >
              Reject
            </button>
            {record.source_url && (
              <a
                href={record.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 border border-gray-300 rounded text-sm text-center hover:bg-gray-50"
              >
                Source →
              </a>
            )}
          </div>
        </div>

        {/* Right: images */}
        <div className="bg-white border rounded-lg p-4">
          <h2 className="font-semibold text-gray-900 mb-3">
            Images ({record.images?.length ?? 0})
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {record.images?.map((img) => (
              <div
                key={img.id}
                className={`relative rounded overflow-hidden border-2 ${
                  img.id === record.primary_image_id ? "border-blue-500" : "border-transparent"
                }`}
              >
                <div className="h-24 bg-gray-100">
                  <ImageThumbnail
                    url={img.url}
                    alt={img.alt_text ?? ""}
                    imageType={img.image_type}
                    className="w-full h-full"
                  />
                </div>
                <div className="p-1 text-xs text-gray-500 flex items-center justify-between">
                  <span>
                    {img.image_type} · {img.confidence}%
                  </span>
                  <button
                    onClick={() => setPrimaryMutation.mutate(img.id)}
                    className={
                      img.id === record.primary_image_id
                        ? "text-yellow-500"
                        : "text-gray-300 hover:text-yellow-500"
                    }
                  >
                    <Star
                      size={14}
                      fill={img.id === record.primary_image_id ? "currentColor" : "none"}
                    />
                  </button>
                </div>
              </div>
            ))}
          </div>
          {(!record.images || record.images.length === 0) && (
            <div className="text-gray-400 text-sm text-center py-4">No images collected.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function renderFieldRow(
  label: string,
  key: keyof ArtRecord,
  getField: (k: keyof ArtRecord) => string | null | undefined,
  setField: (k: keyof ArtRecord, v: unknown) => void,
  editing: boolean,
  textarea = false
) {
  const value = getField(key);
  return (
    <div key={String(key)}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {editing ? (
        textarea ? (
          <textarea
            value={value ?? ""}
            onChange={(e) => setField(key, e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm h-20 focus:ring-2 focus:ring-blue-500"
          />
        ) : (
          <input
            type="text"
            value={value ?? ""}
            onChange={(e) => setField(key, e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
          />
        )
      ) : (
        <div className="text-sm text-gray-800">
          {value ?? <span className="text-gray-400 italic">—</span>}
        </div>
      )}
    </div>
  );
}
