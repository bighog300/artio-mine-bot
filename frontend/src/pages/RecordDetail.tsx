import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveRecord,
  getAdjacentRecords,
  getRecord,
  rejectRecord,
  setPrimaryImage,
  updateRecord,
  type ArtRecord,
} from "@/lib/api";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { RecordTypeBadge } from "@/components/shared/RecordTypeBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TagInput } from "@/components/shared/TagInput";
import { ImageSelectionPanel } from "@/components/records/ImageSelectionPanel";

export function RecordDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<ArtRecord>>({});

  const params = useMemo(() => {
    const search = new URLSearchParams(location.search);
    return {
      source_id: search.get("source_id") ?? undefined,
      status: search.get("status") ?? undefined,
    };
  }, [location.search]);

  const { data: record, isLoading } = useQuery({
    queryKey: ["record", id],
    queryFn: () => getRecord(id!),
    enabled: !!id,
  });

  const { data: adjacent } = useQuery({
    queryKey: ["record-adjacent", id, params],
    queryFn: () => getAdjacentRecords(id!, params),
    enabled: !!id,
  });

  useEffect(() => {
    if (record) {
      setFormData(record);
    }
  }, [record]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<ArtRecord>) => updateRecord(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["record", id] });
      queryClient.invalidateQueries({ queryKey: ["records"] });
    },
  });

  const goToAdjacent = (nextId: string | null) => {
    if (!nextId) return;
    const query = new URLSearchParams();
    if (params.source_id) query.set("source_id", params.source_id);
    if (params.status) query.set("status", params.status);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    navigate(`/records/${nextId}${suffix}`);
  };

  const approveMutation = useMutation({
    mutationFn: () => approveRecord(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["record", id] });
      queryClient.invalidateQueries({ queryKey: ["records"] });
      goToAdjacent(adjacent?.next_id ?? null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectRecord(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["record", id] });
      queryClient.invalidateQueries({ queryKey: ["records"] });
      goToAdjacent(adjacent?.next_id ?? null);
    },
  });

  const setPrimaryMutation = useMutation({
    mutationFn: (imageId: string) => setPrimaryImage(id!, imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["record", id] });
      queryClient.invalidateQueries({ queryKey: ["records"] });
      queryClient.invalidateQueries({ queryKey: ["record-images", id] });
    },
  });

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const inInput = target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (inInput) return;
      if (event.key.toLowerCase() === "a") {
        event.preventDefault();
        approveMutation.mutate();
      }
      if (event.key.toLowerCase() === "r") {
        event.preventDefault();
        rejectMutation.mutate();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [approveMutation, rejectMutation]);

  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!record) return <div className="p-6 text-red-500">Record not found</div>;

  const dirty = JSON.stringify(formData) !== JSON.stringify(record);

  const getField = (key: keyof ArtRecord) => formData[key] as string | null | undefined;
  const setField = (key: keyof ArtRecord, value: unknown) =>
    setFormData((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-sm text-gray-500 hover:text-gray-700">
            ← Back
          </button>
          <RecordTypeBadge type={record.record_type} />
          <StatusBadge status={record.status} />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => goToAdjacent(adjacent?.prev_id ?? null)}
            disabled={!adjacent?.prev_id}
            className="px-3 py-1.5 border border-gray-300 rounded text-sm disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={() => goToAdjacent(adjacent?.next_id ?? null)}
            disabled={!adjacent?.next_id}
            className="px-3 py-1.5 border border-gray-300 rounded text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white border rounded-lg p-4 space-y-3">
          <h1 className="text-xl font-bold">{record.title ?? "Untitled"}</h1>

          {renderFieldRow("Title", "title", getField, setField, false)}
          {renderFieldRow("Description", "description", getField, setField, true)}

          {record.record_type === "artist" && (
            <>
              {renderFieldRow("Bio", "bio", getField, setField, true)}
              {renderFieldRow("Nationality", "nationality", getField, setField, false)}
              {renderFieldRow("Website", "website_url", getField, setField, false)}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Mediums</label>
                <TagInput
                  values={(formData["mediums"] as string[]) ?? []}
                  onChange={(v) => setField("mediums", v)}
                />
              </div>
            </>
          )}

          {(record.record_type === "event" || record.record_type === "exhibition") && (
            <>
              {renderFieldRow("Venue", "venue_name", getField, setField, false)}
              {renderFieldRow("Start Date", "start_date", getField, setField, false)}
              {renderFieldRow("End Date", "end_date", getField, setField, false)}
            </>
          )}

          {record.record_type === "venue" && (
            <>
              {renderFieldRow("Address", "address", getField, setField, false)}
              {renderFieldRow("City", "city", getField, setField, false)}
              {renderFieldRow("Country", "country", getField, setField, false)}
            </>
          )}

          <div className="border-t pt-3">
            <label className="block text-sm font-medium text-gray-700 mb-2">Confidence</label>
            <ConfidenceBar score={record.confidence_score} reasons={record.confidence_reasons} />
            {record.confidence_reasons?.length > 0 && (
              <p className="text-xs text-gray-500 mt-2">
                Confidence signals: {record.confidence_reasons.join(" · ")}
              </p>
            )}
          </div>

          <div className="border-t pt-3 space-y-2">
            <h2 className="font-medium">Image selection</h2>
            <ImageSelectionPanel
              recordId={record.id}
              primaryImageId={record.primary_image_id ?? null}
              onPrimarySet={(imageId) => setPrimaryMutation.mutate(imageId)}
            />
          </div>

          <div className="flex gap-2 border-t pt-3">
            <button
              onClick={() => approveMutation.mutate()}
              className="flex-1 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium"
            >
              Approve (a)
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              className="flex-1 py-2 border border-red-300 text-red-600 rounded hover:bg-red-50 text-sm"
            >
              Reject (r)
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

          {dirty && (
            <button
              onClick={() => updateMutation.mutate(formData)}
              className="w-full py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Save changes
            </button>
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
  textarea = false
) {
  const value = getField(key);
  return (
    <div key={String(key)}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {textarea ? (
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
      )}
    </div>
  );
}
