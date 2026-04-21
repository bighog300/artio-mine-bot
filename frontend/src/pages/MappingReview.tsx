import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveDraftMappingSuggestion,
  getDraftMappingSuggestion,
  getSource,
  triggerMappingCrawl,
  updateDraftMappingSuggestion,
  type MappingFamilyRule,
} from "@/lib/api";
import { Button, Checkbox, Input, Select } from "@/components/ui";

const PAGE_TYPE_OPTIONS = ["listing", "detail", "artist", "artwork", "exhibition", "document", "generic"];
const PRIORITY_OPTIONS = ["high", "medium", "low"];
const PAGINATION_OPTIONS = ["none", "query_param", "path_segment"];
const FRESHNESS_OPTIONS = ["daily", "weekly", "monthly"];

export function MappingReview() {
  const { id: sourceId, mappingId } = useParams<{ id: string; mappingId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const [pendingEdits, setPendingEdits] = useState<Record<string, Partial<MappingFamilyRule>>>({});

  const { data: source } = useQuery({
    queryKey: ["source", sourceId],
    queryFn: () => getSource(sourceId!),
    enabled: !!sourceId,
  });
  const { data: mapping } = useQuery({
    queryKey: ["mapping-suggestion", sourceId, mappingId],
    queryFn: () => getDraftMappingSuggestion(sourceId!, mappingId!),
    enabled: !!sourceId && !!mappingId,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updates = Object.entries(pendingEdits).map(([family_key, patch]) => ({ family_key, ...patch }));
      return updateDraftMappingSuggestion(sourceId!, mappingId!, updates);
    },
    onSuccess: () => {
      setMessage("Draft mapping changes saved.");
      setPendingEdits({});
      qc.invalidateQueries({ queryKey: ["mapping-suggestion", sourceId, mappingId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveDraftMappingSuggestion(sourceId!, mappingId!),
    onSuccess: () => {
      setMessage("Mapping approved and activated.");
      qc.invalidateQueries({ queryKey: ["mapping-suggestion", sourceId, mappingId] });
      qc.invalidateQueries({ queryKey: ["source", sourceId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const crawlMutation = useMutation({
    mutationFn: () => triggerMappingCrawl(sourceId!, mappingId!),
    onSuccess: (payload) => setMessage(`Crawl queued (job ${payload.job_id}).`),
    onError: (err: Error) => setMessage(err.message),
  });

  const familyRows = useMemo(() => {
    const rules = mapping?.family_rules ?? [];
    return rules.map((rule) => ({ ...rule, ...(pendingEdits[rule.family_key] ?? {}) }));
  }, [mapping?.family_rules, pendingEdits]);

  if (!sourceId || !mappingId) {
    return <div className="p-6">Missing source or mapping id.</div>;
  }

  return (
    <div className="space-y-4 lg:space-y-6">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate(`/sources/${sourceId}`)}>← Back to source</Button>
        <h1 className="text-2xl lg:text-3xl font-bold">Mapping Review & Approval</h1>
        <p className="text-sm text-muted-foreground">{source?.url ?? "Loading source..."}</p>
      </div>

      {message && <div className="rounded border border-border bg-muted/40 px-3 py-2 text-sm">{message}</div>}

      <section className="rounded border bg-card p-4 text-sm space-y-1">
        <div>Status: <strong>{mapping?.status ?? "..."}</strong>{mapping?.is_active ? " (active)" : ""}</div>
        <div>Profile: <strong>{mapping?.based_on_profile_id ?? "n/a"}</strong></div>
        <div>Version: <strong>{mapping?.version_number ?? "n/a"}</strong></div>
        <div>Approved at: <strong>{mapping?.approved_at ? new Date(mapping.approved_at).toLocaleString() : "not approved"}</strong></div>
      </section>

      <section className="rounded border bg-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Family rules</h2>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={mapping?.status !== "draft" || Object.keys(pendingEdits).length === 0 || saveMutation.isPending}
          >
            Save edits
          </Button>
        </div>
        <div className="space-y-3">
          {familyRows.map((rule) => (
            <div key={rule.family_key} className="rounded border p-3 space-y-2">
              <div className="text-xs text-muted-foreground">{rule.path_pattern}</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <Select
                  value={rule.page_type}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], page_type: e.target.value } }))}
                  options={PAGE_TYPE_OPTIONS.map((value) => ({ value, label: value }))}
                />
                <Select
                  value={rule.crawl_priority}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], crawl_priority: e.target.value } }))}
                  options={PRIORITY_OPTIONS.map((value) => ({ value, label: value }))}
                />
                <Select
                  value={rule.pagination_mode}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], pagination_mode: e.target.value } }))}
                  options={PAGINATION_OPTIONS.map((value) => ({ value, label: value }))}
                />
                <Select
                  value={rule.freshness_policy}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], freshness_policy: e.target.value } }))}
                  options={FRESHNESS_OPTIONS.map((value) => ({ value, label: value }))}
                />
                <Input
                  value={rule.rationale}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], rationale: e.target.value } }))}
                  placeholder="Rationale"
                />
                <Input
                  value={rule.family_label ?? ""}
                  disabled={mapping?.status !== "draft"}
                  onChange={(e) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], family_label: e.target.value } }))}
                  placeholder="Family label"
                />
              </div>
              <div className="flex items-center gap-4 text-sm">
                <Checkbox
                  id={`include-${rule.family_key}`}
                  checked={rule.include}
                  disabled={mapping?.status !== "draft"}
                  onChange={(checked) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], include: checked } }))}
                  label="Include"
                />
                <Checkbox
                  id={`follow-${rule.family_key}`}
                  checked={rule.follow_links}
                  disabled={mapping?.status !== "draft"}
                  onChange={(checked) => setPendingEdits((prev) => ({ ...prev, [rule.family_key]: { ...prev[rule.family_key], follow_links: checked } }))}
                  label="Follow links"
                />
                <span className="text-xs text-muted-foreground">Confidence: {rule.confidence.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex gap-2">
        {mapping?.status === "draft" && (
          <Button
            variant="primary"
            onClick={() => {
              if (window.confirm("Approve and publish this mapping?")) {
                approveMutation.mutate();
              }
            }}
            disabled={approveMutation.isPending}
          >
            Approve mapping
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={() => crawlMutation.mutate()}
          disabled={mapping?.status !== "approved" || crawlMutation.isPending}
        >
          Start crawl from approved mapping
        </Button>
      </section>
    </div>
  );
}
