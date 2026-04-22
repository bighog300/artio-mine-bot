import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/mobile-utils", () => ({ useIsMobile: () => false }));

const mockedNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockedNavigate,
  };
});

vi.mock("@/lib/api", () => ({
  getSources: vi.fn(),
  getRecords: vi.fn(),
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
    {
      id: "rec-2",
      source_id: "src-1",
      record_type: "event",
      status: "pending",
      title: "Opening Night",
      description: "",
      confidence_score: 0.79,
      confidence_band: "MEDIUM",
      confidence_reasons: ["selector match"],
      source_url: "https://example.test/event-1",
      image_count: 0,
      primary_image_url: null,
      created_at: "2026-04-20T00:00:00Z",
    },
  ],
  total: 2,
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

describe("Records list workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSources).mockResolvedValue({ items: [{ id: "src-1", url: "https://example.test", name: "Example", status: "idle", total_pages: 0, total_records: 0, last_crawled_at: null, created_at: "2026-04-20T00:00:00Z" }], total: 1, skip: 0, limit: 50 } as never);
    vi.mocked(api.getRecords).mockResolvedValue(recordsPayload as never);
  });

  it("navigates to record details when clicking a record row", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("Artist One")).toBeInTheDocument());
    await user.click(screen.getByText("Artist One"));

    expect(mockedNavigate).toHaveBeenCalledWith("/records/rec-1");
  });

  it("refetches records when retry is clicked", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByText("Artist One")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(api.getRecords).toHaveBeenCalledTimes(2));
  });

  it("filters records by type using the record type selector", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Artist One")).toBeInTheDocument();
      expect(screen.getByText("Opening Night")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getAllByRole("combobox")[2], "event");

    await waitFor(() => {
      expect(api.getRecords).toHaveBeenLastCalledWith(expect.objectContaining({ record_type: "event" }));
    });
  });
});
