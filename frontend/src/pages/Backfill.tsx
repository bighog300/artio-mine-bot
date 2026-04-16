import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createBackfillSchedule,
  getBackfillCampaigns,
  getBackfillSchedules,
  type BackfillCampaign,
  type BackfillSchedule,
} from "@/lib/api";
import { Badge, Button, Input } from "@/components/ui";

const statusClass: Record<string, string> = {
  pending: "bg-muted text-muted-foreground",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export function Backfill() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("Weekly Artist Refresh");
  const [cron, setCron] = useState("0 2 * * 0");
  const [limit, setLimit] = useState(100);

  const { data: campaigns, isLoading: campaignsLoading } = useQuery({
    queryKey: ["backfill-campaigns"],
    queryFn: getBackfillCampaigns,
  });

  const { data: schedules, isLoading: schedulesLoading } = useQuery({
    queryKey: ["backfill-schedules"],
    queryFn: getBackfillSchedules,
  });

  const createSchedule = useMutation({
    mutationFn: createBackfillSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backfill-schedules"] });
    },
  });

  const running = (campaigns?.items ?? []).filter((c) => c.status === "running").length;

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createSchedule.mutate({
      name,
      schedule_type: "recurring",
      cron_expression: cron,
      filters: { record_type: "artist", min_completeness: 0, max_completeness: 70 },
      options: { limit },
      auto_start: false,
      enabled: true,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Backfill Dashboard</h1>
        <p className="text-sm text-muted-foreground">Manage campaigns, schedules, and enrichment automation.</p>
      </div>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Total Campaigns" value={(campaigns?.items ?? []).length} />
        <StatCard label="Running" value={running} />
        <StatCard label="Schedules" value={(schedules?.items ?? []).length} />
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-lg font-semibold text-foreground">Create Schedule</h2>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={onSubmit}>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Schedule name"
            required
          />
          <Input
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            placeholder="Cron expression"
            required
          />
          <Input
            type="number"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            min={1}
            max={1000}
          />
          <Button
            type="submit"
            disabled={createSchedule.isPending}
            loading={createSchedule.isPending}
          >
            {createSchedule.isPending ? "Creating…" : "Create"}
          </Button>
        </form>
        {createSchedule.isError ? (
          <p className="mt-2 text-sm text-red-600">{(createSchedule.error as Error).message}</p>
        ) : null}
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-lg font-semibold text-foreground">Recent Campaigns</h2>
        {campaignsLoading ? <p className="text-sm text-muted-foreground">Loading campaigns…</p> : <CampaignTable items={campaigns?.items ?? []} />}
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-lg font-semibold text-foreground">Schedules</h2>
        {schedulesLoading ? <p className="text-sm text-muted-foreground">Loading schedules…</p> : <ScheduleTable items={schedules?.items ?? []} />}
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
    </div>
  );
}

function CampaignTable({ items }: { items: BackfillCampaign[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No campaigns created yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="py-2">Name</th>
            <th className="py-2">Status</th>
            <th className="py-2">Progress</th>
            <th className="py-2">Updated</th>
          </tr>
        </thead>
        <tbody>
          {items.map((campaign) => (
            <tr key={campaign.id} className="border-b border-border/60">
              <td className="py-2 text-foreground">{campaign.name}</td>
              <td className="py-2">
                <Badge className={statusClass[campaign.status] ?? "bg-muted text-muted-foreground"}>
                  {campaign.status}
                </Badge>
              </td>
              <td className="py-2 text-muted-foreground">
                {campaign.processed_records}/{campaign.total_records}
              </td>
              <td className="py-2 text-muted-foreground">{new Date(campaign.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScheduleTable({ items }: { items: BackfillSchedule[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No schedules configured.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="py-2">Name</th>
            <th className="py-2">Cron</th>
            <th className="py-2">Next Run</th>
            <th className="py-2">Enabled</th>
          </tr>
        </thead>
        <tbody>
          {items.map((schedule) => (
            <tr key={schedule.id} className="border-b border-border/60">
              <td className="py-2 text-foreground">{schedule.name}</td>
              <td className="py-2 text-muted-foreground">{schedule.cron_expression ?? "-"}</td>
              <td className="py-2 text-muted-foreground">
                {schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : "-"}
              </td>
              <td className="py-2 text-muted-foreground">{schedule.enabled ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
