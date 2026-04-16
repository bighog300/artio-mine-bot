import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { DuplicateResolution } from "@/pages/DuplicateResolution";

vi.mock("@/lib/api", () => ({
  getDuplicates: vi.fn(),
  getDuplicatePair: vi.fn(),
  mergeDuplicates: vi.fn(),
  dismissDuplicate: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DuplicateResolution />
    </QueryClientProvider>
  );
}

describe("DuplicateResolution", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no duplicates", async () => {
    vi.mocked(api.getDuplicates).mockResolvedValue({ items: [], total: 0 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("No Duplicates Found")).toBeInTheDocument();
    });
  });

  it("displays duplicate pair details", async () => {
    vi.mocked(api.getDuplicates).mockResolvedValue({
      items: [
        {
          id: "pair-1",
          record_a_id: "rec-a",
          record_b_id: "rec-b",
          similarity_score: 85,
          matching_fields: ["nationality"],
          conflicting_fields: [{ field: "title", value_a: "John Doe", value_b: "J. Doe" }],
          suggested_action: "merge",
          status: "pending",
        },
      ],
      total: 1,
    });

    vi.mocked(api.getDuplicatePair).mockResolvedValue({
      pair: {
        id: "pair-1",
        record_a_id: "rec-a",
        record_b_id: "rec-b",
        similarity_score: 85,
        matching_fields: ["nationality"],
        conflicting_fields: [{ field: "title", value_a: "John Doe", value_b: "J. Doe" }],
        suggested_action: "merge",
        status: "pending",
      },
      record_a: {
        id: "rec-a",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "John Doe",
        description: null,
        confidence_score: 70,
        confidence_band: "MEDIUM",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
      record_b: {
        id: "rec-b",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "J. Doe",
        description: null,
        confidence_score: 71,
        confidence_band: "MEDIUM",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText("Record A").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Record B").length).toBeGreaterThan(0);
      expect(screen.getAllByText("John Doe").length).toBeGreaterThan(0);
      expect(screen.getAllByText("J. Doe").length).toBeGreaterThan(0);
      expect(screen.getByText("85%")).toBeInTheDocument();
    });
  });

  it("allows merge with selected strategy", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getDuplicates).mockResolvedValue({
      items: [
        {
          id: "pair-1",
          record_a_id: "rec-a",
          record_b_id: "rec-b",
          similarity_score: 91,
          matching_fields: [],
          conflicting_fields: [{ field: "title", value_a: "John", value_b: "Johnny" }],
          suggested_action: "merge",
          status: "pending",
        },
      ],
      total: 1,
    });

    vi.mocked(api.getDuplicatePair).mockResolvedValue({
      pair: {
        id: "pair-1",
        record_a_id: "rec-a",
        record_b_id: "rec-b",
        similarity_score: 91,
        matching_fields: [],
        conflicting_fields: [{ field: "title", value_a: "John", value_b: "Johnny" }],
        suggested_action: "merge",
        status: "pending",
      },
      record_a: {
        id: "rec-a",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "John",
        description: null,
        confidence_score: 80,
        confidence_band: "HIGH",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
      record_b: {
        id: "rec-b",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "Johnny",
        description: null,
        confidence_score: 79,
        confidence_band: "HIGH",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
    });

    vi.mocked(api.mergeDuplicates).mockResolvedValue({ status: "merge" });

    renderPage();

    await waitFor(() => expect(screen.getByText("Resolve Conflicts (1)")).toBeInTheDocument());

    await user.click(screen.getByLabelText("title record b"));
    await user.click(screen.getByText("Merge Records"));

    await waitFor(() => {
      expect(api.mergeDuplicates).toHaveBeenCalledWith("pair-1", "rec-a", expect.objectContaining({ title: "b" }));
    });
  });

  it("allows dismissing duplicate", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getDuplicates).mockResolvedValue({
      items: [
        {
          id: "pair-1",
          record_a_id: "rec-a",
          record_b_id: "rec-b",
          similarity_score: 88,
          matching_fields: [],
          conflicting_fields: [],
          suggested_action: "merge",
          status: "pending",
        },
      ],
      total: 1,
    });

    vi.mocked(api.getDuplicatePair).mockResolvedValue({
      pair: {
        id: "pair-1",
        record_a_id: "rec-a",
        record_b_id: "rec-b",
        similarity_score: 88,
        matching_fields: [],
        conflicting_fields: [],
        suggested_action: "merge",
        status: "pending",
      },
      record_a: {
        id: "rec-a",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "A",
        description: null,
        confidence_score: 80,
        confidence_band: "HIGH",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
      record_b: {
        id: "rec-b",
        source_id: "src-1",
        record_type: "artist",
        status: "pending",
        title: "B",
        description: null,
        confidence_score: 80,
        confidence_band: "HIGH",
        confidence_reasons: [],
        source_url: null,
        created_at: "2026-04-16T00:00:00Z",
      },
    });

    vi.mocked(api.dismissDuplicate).mockResolvedValue({
      id: "pair-1",
      record_a_id: "rec-a",
      record_b_id: "rec-b",
      similarity_score: 0,
      matching_fields: [],
      conflicting_fields: [],
      suggested_action: "keep_both",
      status: "not_duplicate",
    });

    renderPage();

    await user.click(await screen.findByText("Not Duplicate"));

    await waitFor(() => {
      expect(api.dismissDuplicate).toHaveBeenCalledWith("pair-1");
    });
  });

  it("supports keyboard next navigation", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getDuplicates).mockResolvedValue({
      items: [
        {
          id: "pair-1",
          record_a_id: "rec-a",
          record_b_id: "rec-b",
          similarity_score: 90,
          matching_fields: [],
          conflicting_fields: [],
          suggested_action: "merge",
          status: "pending",
        },
        {
          id: "pair-2",
          record_a_id: "rec-c",
          record_b_id: "rec-d",
          similarity_score: 85,
          matching_fields: [],
          conflicting_fields: [],
          suggested_action: "merge",
          status: "pending",
        },
      ],
      total: 2,
    });

    vi.mocked(api.getDuplicatePair).mockImplementation((id: string) =>
      Promise.resolve({
        pair: {
          id,
          record_a_id: id === "pair-1" ? "rec-a" : "rec-c",
          record_b_id: id === "pair-1" ? "rec-b" : "rec-d",
          similarity_score: id === "pair-1" ? 90 : 85,
          matching_fields: [],
          conflicting_fields: [],
          suggested_action: "merge",
          status: "pending",
        },
        record_a: {
          id: id === "pair-1" ? "rec-a" : "rec-c",
          source_id: "src-1",
          record_type: "artist",
          status: "pending",
          title: "A",
          description: null,
          confidence_score: 80,
          confidence_band: "HIGH",
          confidence_reasons: [],
          source_url: null,
          created_at: "2026-04-16T00:00:00Z",
        },
        record_b: {
          id: id === "pair-1" ? "rec-b" : "rec-d",
          source_id: "src-1",
          record_type: "artist",
          status: "pending",
          title: "B",
          description: null,
          confidence_score: 80,
          confidence_band: "HIGH",
          confidence_reasons: [],
          source_url: null,
          created_at: "2026-04-16T00:00:00Z",
        },
      })
    );

    renderPage();

    await waitFor(() => expect(screen.getByText("90%")).toBeInTheDocument());

    await user.keyboard("n");

    await waitFor(() => expect(screen.getByText("85%")).toBeInTheDocument());
  });
});
