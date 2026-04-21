import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getSource: vi.fn(),
  getDraftMappingSuggestion: vi.fn(),
  updateDraftMappingSuggestion: vi.fn(),
  approveDraftMappingSuggestion: vi.fn(),
  triggerMappingCrawl: vi.fn(),
}));

import { MappingReview } from "@/pages/MappingReview";
import * as api from "@/lib/api";

const mappingPayload = {
  id: "map-1",
  source_id: "src-1",
  based_on_profile_id: "profile-1",
  version_number: 3,
  status: "draft",
  is_active: false,
  approved_at: null,
  approved_by: null,
  superseded_at: null,
  created_at: "2026-04-21T00:00:00Z",
  diagnostics: {},
  family_rules: [
    {
      family_key: "family:artists",
      family_label: "Artists",
      path_pattern: "/artists",
      page_type: "listing",
      include: true,
      follow_links: true,
      crawl_priority: "high",
      pagination_mode: "query_param",
      freshness_policy: "weekly",
      confidence: 0.91,
      rationale: "seed",
      diagnostics_summary: {},
    },
  ],
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/sources/src-1/mappings/map-1/review"]}>
        <Routes>
          <Route path="/sources/:id/mappings/:mappingId/review" element={<MappingReview />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("MappingReview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSource).mockResolvedValue({ id: "src-1", url: "https://example.test" } as never);
    vi.mocked(api.getDraftMappingSuggestion).mockResolvedValue(mappingPayload as never);
    vi.mocked(api.updateDraftMappingSuggestion).mockResolvedValue(mappingPayload as never);
    vi.mocked(api.approveDraftMappingSuggestion).mockResolvedValue({ ...mappingPayload, status: "approved" } as never);
    vi.mocked(api.triggerMappingCrawl).mockResolvedValue({
      source_id: "src-1",
      mapping_id: "map-1",
      job_id: "job-1",
      queue_job_id: "rq-1",
      status: "queued",
      message: "ok",
    });
  });

  it("renders the review page", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("/artists")).toBeInTheDocument());
  });

  it("edits rule values and saves", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => expect(screen.getByDisplayValue("listing")).toBeInTheDocument());
    await user.selectOptions(screen.getByDisplayValue("listing"), "artist");
    await user.click(screen.getByRole("button", { name: "Save edits" }));

    await waitFor(() => {
      expect(api.updateDraftMappingSuggestion).toHaveBeenCalledWith("src-1", "map-1", expect.any(Array));
    });
  });

  it("shows approve button for draft mappings", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve mapping" })).toBeInTheDocument());
  });

  it("keeps crawl action disabled for draft mappings", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Start crawl from approved mapping" })).toBeDisabled());
  });
});
