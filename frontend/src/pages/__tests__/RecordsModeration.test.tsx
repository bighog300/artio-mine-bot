import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/mobile-utils", () => ({ useIsMobile: () => false }));

vi.mock("@/lib/api", () => ({
  getSources: vi.fn(),
  getRecords: vi.fn(),
  approveRecord: vi.fn(),
  rejectRecord: vi.fn(),
  bulkApprove: vi.fn(),
}));

import { Records } from "@/pages/Records";
import * as api from "@/lib/api";

const recordsPayload = {
  items: [
    {
      id: "rec-1",
      source_id: "src-1",
      record_type: "artist",
      status: "pending",
      title: "Artist One",
      description: "",
      confidence_score: 0.91,
      confidence_band: "HIGH",
      confidence_reasons: ["strong extraction"],
      source_url: "https://example.test/artist-1",
      image_count: 0,
      primary_image_url: null,
      created_at: "2026-04-20T00:00:00Z",
    },
  ],
  total: 1,
  skip: 0,
  limit: 25,
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Records />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Records moderation actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSources).mockResolvedValue({ items: [{ id: "src-1", url: "https://example.test", name: "Example", status: "idle", total_pages: 0, total_records: 0, last_crawled_at: null, created_at: "2026-04-20T00:00:00Z" }], total: 1, skip: 0, limit: 50 } as never);
    vi.mocked(api.getRecords).mockResolvedValue(recordsPayload as never);
    vi.mocked(api.approveRecord).mockResolvedValue({ id: "rec-1", status: "approved" } as never);
    vi.mocked(api.rejectRecord).mockResolvedValue({ id: "rec-1", status: "rejected" } as never);
    vi.mocked(api.bulkApprove).mockResolvedValue({ approved_count: 1 });
  });

  it("sends reject reason when rejecting from queue", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "prompt").mockReturnValue("Not relevant");
    renderPage();

    await waitFor(() => expect(screen.getByText("Artist One")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "✕" }));

    await waitFor(() => expect(api.rejectRecord).toHaveBeenCalledWith("rec-1", "Not relevant"));
  });

  it("approves record from queue", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("Artist One")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "✓" }));

    await waitFor(() => expect(api.approveRecord).toHaveBeenCalled());
    expect(vi.mocked(api.approveRecord).mock.calls[0][0]).toBe("rec-1");
  });
});
