import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Backfill } from "@/pages/Backfill";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getBackfillCampaigns: vi.fn(),
  getBackfillSchedules: vi.fn(),
  createBackfillSchedule: vi.fn(),
}));

function renderBackfill() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <Backfill />
    </QueryClientProvider>
  );
}

describe("Backfill page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state while data is pending", () => {
    vi.mocked(api.getBackfillCampaigns).mockImplementation(() => new Promise(() => {}));
    vi.mocked(api.getBackfillSchedules).mockImplementation(() => new Promise(() => {}));

    renderBackfill();

    expect(screen.getByText("Loading campaigns…")).toBeInTheDocument();
    expect(screen.getByText("Loading schedules…")).toBeInTheDocument();
  });

  it("shows KPI cards from loaded data", async () => {
    vi.mocked(api.getBackfillCampaigns).mockResolvedValue({
      items: [
        {
          id: "c1",
          source_id: "s1",
          name: "Artist Backfill",
          status: "running",
          total_records: 120,
          processed_records: 40,
          successful_updates: 30,
          failed_updates: 10,
          started_at: "2026-04-15T00:00:00Z",
          completed_at: null,
          created_at: "2026-04-15T00:00:00Z",
          updated_at: "2026-04-15T01:00:00Z",
        },
        {
          id: "c2",
          source_id: "s1",
          name: "Venue Backfill",
          status: "completed",
          total_records: 50,
          processed_records: 50,
          successful_updates: 48,
          failed_updates: 2,
          started_at: "2026-04-14T00:00:00Z",
          completed_at: "2026-04-14T02:00:00Z",
          created_at: "2026-04-14T00:00:00Z",
          updated_at: "2026-04-14T02:00:00Z",
        },
      ],
      total: 2,
    });
    vi.mocked(api.getBackfillSchedules).mockResolvedValue({ items: [], total: 0 });

    renderBackfill();

    await waitFor(() => {
      expect(screen.getByText("Total Campaigns")).toBeInTheDocument();
      expect(screen.getByText("Running")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Schedules" })).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("No schedules configured.")).toBeInTheDocument();
    });
  });

  it("renders campaign and schedule tables", async () => {
    vi.mocked(api.getBackfillCampaigns).mockResolvedValue({
      items: [
        {
          id: "c1",
          source_id: "s1",
          name: "Artist Bio Enrichment",
          status: "completed",
          total_records: 100,
          processed_records: 100,
          successful_updates: 95,
          failed_updates: 5,
          started_at: "2026-04-01T00:00:00Z",
          completed_at: "2026-04-01T01:00:00Z",
          created_at: "2026-04-01T00:00:00Z",
          updated_at: "2026-04-01T01:00:00Z",
        },
      ],
      total: 1,
    });
    vi.mocked(api.getBackfillSchedules).mockResolvedValue({
      items: [
        {
          id: "sch1",
          name: "Weekly Artist Refresh",
          schedule_type: "recurring",
          cron_expression: "0 2 * * 0",
          filters: {},
          options: {},
          auto_start: false,
          enabled: true,
          next_run_at: "2026-04-20T02:00:00Z",
          created_at: "2026-04-16T00:00:00Z",
          updated_at: "2026-04-16T00:00:00Z",
        },
      ],
      total: 1,
    });

    renderBackfill();

    await waitFor(() => {
      expect(screen.getByText("Artist Bio Enrichment")).toBeInTheDocument();
      expect(screen.getByText("completed")).toBeInTheDocument();
      expect(screen.getByText("Weekly Artist Refresh")).toBeInTheDocument();
      expect(screen.getByText("0 2 * * 0")).toBeInTheDocument();
      expect(screen.getByText("Yes")).toBeInTheDocument();
    });
  });

  it("shows empty campaign state", async () => {
    vi.mocked(api.getBackfillCampaigns).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.getBackfillSchedules).mockResolvedValue({ items: [], total: 0 });

    renderBackfill();

    await waitFor(() => {
      expect(screen.getByText("No campaigns created yet.")).toBeInTheDocument();
      expect(screen.getByText("No schedules configured.")).toBeInTheDocument();
    });
  });

  it("creates schedule and refetches schedules on success", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getBackfillCampaigns).mockResolvedValue({ items: [], total: 0 });
    const getSchedulesMock = vi.mocked(api.getBackfillSchedules).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.createBackfillSchedule).mockResolvedValue({
      id: "sch2",
      name: "Nightly Update",
      schedule_type: "recurring",
      cron_expression: "0 1 * * *",
      filters: {},
      options: {},
      auto_start: false,
      enabled: true,
      next_run_at: null,
      created_at: "2026-04-16T00:00:00Z",
      updated_at: "2026-04-16T00:00:00Z",
    });

    renderBackfill();

    await waitFor(() => expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument());

    const nameInput = screen.getByPlaceholderText("Schedule name");
    const cronInput = screen.getByPlaceholderText("Cron expression");
    const limitInput = screen.getByRole("spinbutton");

    await user.clear(nameInput);
    await user.type(nameInput, "Nightly Update");
    await user.clear(cronInput);
    await user.type(cronInput, "0 1 * * *");
    await user.clear(limitInput);
    await user.type(limitInput, "300");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(api.createBackfillSchedule).toHaveBeenCalled();
      expect(vi.mocked(api.createBackfillSchedule).mock.calls[0][0]).toEqual(
        expect.objectContaining({
          name: "Nightly Update",
          cron_expression: "0 1 * * *",
          options: { limit: 300 },
        })
      );
    });

    await waitFor(() => {
      expect(getSchedulesMock).toHaveBeenCalledTimes(2);
    });
  });

  it("shows mutation error when schedule creation fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.getBackfillCampaigns).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.getBackfillSchedules).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.createBackfillSchedule).mockRejectedValue(new Error("Invalid cron expression"));

    renderBackfill();

    await waitFor(() => expect(screen.getByRole("button", { name: "Create" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid cron expression")).toBeInTheDocument();
    });
  });
});
