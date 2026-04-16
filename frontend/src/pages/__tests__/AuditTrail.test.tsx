import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuditTrail } from "@/pages/AuditTrail";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getAuditTrail: vi.fn(),
  getAuditEvent: vi.fn(),
  exportAuditTrail: vi.fn(),
}));

const baseEvents = {
  items: [
    {
      id: "evt-1",
      timestamp: "2026-04-16T10:00:00Z",
      event_type: "update",
      entity_type: "record",
      entity_id: "rec-1",
      user_id: "admin",
      user_name: "Admin",
      source_id: "src-1",
      record_id: "rec-1",
      message: "Updated record",
      changes: { before: { title: "Old" }, after: { title: "New" } },
      metadata: { reason: "manual" },
    },
  ],
  total: 1,
  skip: 0,
  limit: 25,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuditTrail />
    </QueryClientProvider>
  );
}

describe("AuditTrail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getAuditTrail).mockResolvedValue(baseEvents);
    vi.mocked(api.getAuditEvent).mockResolvedValue(baseEvents.items[0]);
    vi.mocked(api.exportAuditTrail).mockResolvedValue("id,event_type\n1,update\n");
  });

  it("displays audit events", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Updated record")).toBeInTheDocument());
  });

  it("filters by event type", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("Updated record")).toBeInTheDocument());
    await user.selectOptions(screen.getByDisplayValue("All events"), "update");

    await waitFor(() => {
      expect(api.getAuditTrail).toHaveBeenLastCalledWith(expect.objectContaining({ event_type: "update" }));
    });
  });

  it("filters by entity type", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.selectOptions(screen.getByDisplayValue("All entities"), "record");

    await waitFor(() => {
      expect(api.getAuditTrail).toHaveBeenLastCalledWith(expect.objectContaining({ entity_type: "record" }));
    });
  });

  it("filters by date range", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();

    const dateInputs = container.querySelectorAll('input[type="date"]');
    await user.type(dateInputs[0] as HTMLInputElement, "2026-04-01");
    await user.type(dateInputs[1] as HTMLInputElement, "2026-04-16");

    await waitFor(() => {
      expect(api.getAuditTrail).toHaveBeenLastCalledWith(
        expect.objectContaining({ date_from: "2026-04-01", date_to: "2026-04-16" })
      );
    });
  });

  it("searches events", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText("Search message, entity, user"), "record");

    await waitFor(() => {
      expect(api.getAuditTrail).toHaveBeenLastCalledWith(expect.objectContaining({ search: "record" }));
    });
  });

  it("shows event details on click", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("Updated record")).toBeInTheDocument());
    await user.click(screen.getByText("Updated record"));

    await waitFor(() => {
      expect(api.getAuditEvent).toHaveBeenCalledWith("evt-1");
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Before")).toBeInTheDocument();
      expect(screen.getByText("After")).toBeInTheDocument();
    });
  });

  it("exports audit log", async () => {
    const user = userEvent.setup();
    Object.defineProperty(URL, "createObjectURL", { writable: true, value: vi.fn(() => "blob:test") });
    Object.defineProperty(URL, "revokeObjectURL", { writable: true, value: vi.fn() });
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    const revokeObjectURL = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    renderPage();

    await user.click(screen.getByRole("button", { name: "Export CSV" }));

    await waitFor(() => {
      expect(api.exportAuditTrail).toHaveBeenCalled();
      expect(createObjectURL).toHaveBeenCalled();
      expect(revokeObjectURL).toHaveBeenCalled();
    });

    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });
});
