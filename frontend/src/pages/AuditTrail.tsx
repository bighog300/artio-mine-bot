import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { AuditEventModal } from "@/components/audit/AuditEventModal";
import { AuditFilterBar, type AuditFilters } from "@/components/audit/AuditFilterBar";
import { AuditTimeline } from "@/components/audit/AuditTimeline";
import { Button } from "@/components/ui";
import { exportAuditTrail, getAuditEvent, getAuditTrail, type AuditEvent } from "@/lib/api";

const PAGE_SIZE = 25;

const DEFAULT_FILTERS: AuditFilters = {
  event_type: "",
  entity_type: "",
  user_id: "",
  date_from: "",
  date_to: "",
  search: "",
};

function toQuery(filters: AuditFilters, skip: number) {
  return {
    event_type: filters.event_type || undefined,
    entity_type: filters.entity_type || undefined,
    user_id: filters.user_id || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    search: filters.search || undefined,
    skip,
    limit: PAGE_SIZE,
  };
}

function downloadCsv(csvContent: string, filename: string) {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

export function AuditTrail() {
  const [filters, setFilters] = useState<AuditFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const skip = (page - 1) * PAGE_SIZE;
  const queryParams = useMemo(() => toQuery(filters, skip), [filters, skip]);

  const eventsQuery = useQuery({
    queryKey: ["audit-events", queryParams],
    queryFn: () => getAuditTrail(queryParams),
    refetchInterval: 30_000,
  });

  const selectedEventQuery = useQuery({
    queryKey: ["audit-event", selectedEventId],
    queryFn: () => getAuditEvent(selectedEventId as string),
    enabled: Boolean(selectedEventId),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportAuditTrail(toQuery(filters, 0)),
    onSuccess: (csv) => {
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      downloadCsv(csv, `audit-trail-${stamp}.csv`);
    },
  });

  const totalPages = Math.max(1, Math.ceil((eventsQuery.data?.total ?? 0) / PAGE_SIZE));
  const selectedEvent = (selectedEventQuery.data ?? null) as AuditEvent | null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
          <p className="text-sm text-gray-600">Track create/update/delete/approval activity across sources and records.</p>
        </div>
        <div className="text-sm text-gray-600">Auto-refresh: every 30s</div>
      </div>

      <AuditFilterBar
        filters={filters}
        onChange={(next) => {
          setFilters(next);
          setPage(1);
        }}
        onExport={() => exportMutation.mutate()}
        isExporting={exportMutation.isPending}
      />

      {eventsQuery.isLoading ? (
        <div className="rounded-lg border bg-white p-6 text-sm text-gray-500">Loading audit events…</div>
      ) : eventsQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          Failed to load audit events: {(eventsQuery.error as Error).message}
        </div>
      ) : (
        <AuditTimeline events={eventsQuery.data?.items ?? []} onSelectEvent={(event) => setSelectedEventId(event.id)} />
      )}

      <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 text-sm">
        <p>
          Showing {eventsQuery.data?.items.length ?? 0} of {eventsQuery.data?.total ?? 0} events
        </p>
        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            Previous
          </Button>
          <span>Page {page} / {totalPages}</span>
          <Button type="button" variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
            Next
          </Button>
        </div>
      </div>

      {selectedEventId && selectedEvent && <AuditEventModal event={selectedEvent} onClose={() => setSelectedEventId(null)} />}
    </div>
  );
}
