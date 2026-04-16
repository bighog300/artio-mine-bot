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
import { TagInput } from "@/components/shared/TagInput";
import { ImageSelectionPanel } from "@/components/records/ImageSelectionPanel";
import { Alert, Badge, Button, Input, TextArea } from "@/components/ui";

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
  const hasConflictSignals =
    record.confidence_band === "LOW" ||
    record.confidence_reasons.some((reason) => reason.toLowerCase().includes("conflict"));

  const getField = (key: keyof ArtRecord) => formData[key] as string | null | undefined;
  const setField = (key: keyof ArtRecord, value: unknown) =>
    setFormData((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button onClick={() => navigate(-1)} variant="ghost" size="sm">
            ← Back
          </Button>
          <Badge>{record.record_type}</Badge>
          <Badge>{record.status}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => goToAdjacent(adjacent?.prev_id ?? null)}
            disabled={!adjacent?.prev_id}
            variant="secondary"
            size="sm"
          >
            Prev
          </Button>
          <Button
            onClick={() => goToAdjacent(adjacent?.next_id ?? null)}
            disabled={!adjacent?.next_id}
            variant="secondary"
            size="sm"
          >
            Next
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white border rounded-lg p-4 space-y-3">
          <h1 className="text-xl font-bold">{record.title ?? "Untitled"}</h1>
          {hasConflictSignals && (
            <Alert
              variant="warning"
              title="Potential record conflict detected"
              description="Review this record carefully before approving. Confidence signals indicate conflicting or low-confidence extracted fields."
            />
          )}

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
            <Button
              onClick={() => approveMutation.mutate()}
              className="flex-1"
            >
              Approve (a)
            </Button>
            <Button
              onClick={() => rejectMutation.mutate()}
              className="flex-1"
              variant="danger"
            >
              Reject (r)
            </Button>
            {record.source_url && (
              <a
                href={record.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-10 flex-1 items-center justify-center rounded-md border border-gray-300 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Source →
              </a>
            )}
          </div>

          {dirty && (
            <Button
              onClick={() => updateMutation.mutate(formData)}
              className="w-full"
              loading={updateMutation.isPending}
            >
              Save changes
            </Button>
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
        <TextArea
          value={value ?? ""}
          onChange={(e) => setField(key, e.target.value)}
          className="h-20"
        />
      ) : (
        <Input
          type="text"
          value={value ?? ""}
          onChange={(e) => setField(key, e.target.value)}
        />
      )}
    </div>
  );
}
