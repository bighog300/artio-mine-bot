import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  acknowledgeDriftSignal,
  createRemapDraftFromDriftSignal,
  detectSourceDriftSignals,
  dismissDriftSignal,
  getSource,
  getSourceDriftSignals,
} from "@/lib/api";
import { Button, Select } from "@/components/ui";

export function MappingDrift() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("open");

  const { data: source } = useQuery({ queryKey: ["source", id], queryFn: () => getSource(id!), enabled: !!id });
  const { data, isLoading } = useQuery({
    queryKey: ["source-drift-signals", id, statusFilter],
    queryFn: () => getSourceDriftSignals(id!, { status: statusFilter }),
    enabled: !!id,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["source-drift-signals", id] });

  const detectMutation = useMutation({ mutationFn: () => detectSourceDriftSignals(id!), onSuccess: refresh });
  const ackMutation = useMutation({ mutationFn: (signalId: string) => acknowledgeDriftSignal(id!, signalId), onSuccess: refresh });
  const dismissMutation = useMutation({ mutationFn: (signalId: string) => dismissDriftSignal(id!, signalId), onSuccess: refresh });
  const remapMutation = useMutation({
    mutationFn: (signalId: string) => createRemapDraftFromDriftSignal(id!, signalId),
    onSuccess: (res) => navigate(`/sources/${id}/mapping?draft=${res.draft_mapping_version_id}`),
  });

  const healthTone = useMemo(() => {
    if (data?.mapping_health === "stale") return "text-red-600";
    if (data?.mapping_health === "warning") return "text-amber-600";
    return "text-emerald-600";
  }, [data?.mapping_health]);

  if (!id) return <div className="text-red-500">Missing source id</div>;
  if (isLoading) return <div className="text-muted-foreground">Loading drift signals...</div>;

  return (
    <div className="space-y-4">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/sources/${id}`)} className="mb-2">← Source</Button>
        <h1 className="text-2xl font-bold">Mapping Drift Review</h1>
        <p className="text-sm text-muted-foreground">{source?.name ?? source?.url}</p>
      </div>

      <div className="rounded border bg-card p-4 text-sm">
        <div>Active mapping version: <strong>{data?.active_mapping_version_id ?? "none"}</strong></div>
        <div className={healthTone}>Mapping health: <strong>{data?.mapping_health ?? "healthy"}</strong></div>
        <div>Open high-severity signals: <strong>{data?.open_high_severity ?? 0}</strong></div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={() => detectMutation.mutate()} disabled={detectMutation.isPending}>Run drift detection</Button>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            options={[
              { value: "open", label: "Open" },
              { value: "acknowledged", label: "Acknowledged" },
              { value: "resolved", label: "Resolved" },
              { value: "dismissed", label: "Dismissed" },
            ]}
          />
        </div>
      </div>

      <div className="rounded border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="p-2 text-left">Type</th>
              <th className="p-2 text-left">Severity</th>
              <th className="p-2 text-left">Family</th>
              <th className="p-2 text-left">Detected</th>
              <th className="p-2 text-left">Status</th>
              <th className="p-2 text-left">Diagnostics</th>
              <th className="p-2 text-left">Proposed Action</th>
              <th className="p-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((signal) => (
              <tr key={signal.id} className="border-t align-top">
                <td className="p-2">{signal.signal_type}</td>
                <td className="p-2">{signal.severity}</td>
                <td className="p-2">{signal.family_key ?? "—"}</td>
                <td className="p-2">{new Date(signal.detected_at).toLocaleString()}</td>
                <td className="p-2">{signal.status}</td>
                <td className="p-2 max-w-[280px] truncate">{JSON.stringify(signal.diagnostics)}</td>
                <td className="p-2">{signal.proposed_action ?? "—"}</td>
                <td className="p-2 space-y-1">
                  <Button size="sm" variant="secondary" onClick={() => ackMutation.mutate(signal.id)} disabled={signal.status !== "open"}>Acknowledge</Button>
                  <Button size="sm" variant="secondary" onClick={() => dismissMutation.mutate(signal.id)} disabled={signal.status === "dismissed"}>Dismiss</Button>
                  <Button size="sm" onClick={() => remapMutation.mutate(signal.id)}>Create remap draft</Button>
                  {signal.mapping_version_id ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        navigate(
                          `/mappings/${signal.mapping_version_id}?source_id=${encodeURIComponent(id)}&signal_id=${encodeURIComponent(signal.id)}&field=${encodeURIComponent(signal.family_key ?? "")}`,
                        )
                      }
                    >
                      Fix Mapping
                    </Button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
