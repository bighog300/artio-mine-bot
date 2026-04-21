import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getSource: vi.fn(),
  getSourceDriftSignals: vi.fn(),
  detectSourceDriftSignals: vi.fn(),
  acknowledgeDriftSignal: vi.fn(),
  dismissDriftSignal: vi.fn(),
  createRemapDraftFromDriftSignal: vi.fn(),
}));

import { MappingDrift } from "@/pages/MappingDrift";
import * as api from "@/lib/api";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/sources/src-1/drift"]}>
        <Routes>
          <Route path="/sources/:id/drift" element={<MappingDrift />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("MappingDrift", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSource).mockResolvedValue({ id: "src-1", url: "https://example.test" } as never);
    vi.mocked(api.getSourceDriftSignals).mockResolvedValue({
      source_id: "src-1",
      active_mapping_version_id: "map-1",
      mapping_health: "warning",
      open_high_severity: 1,
      total: 1,
      items: [
        {
          id: "sig-1",
          source_id: "src-1",
          mapping_version_id: "map-1",
          family_key: "family:artists",
          signal_type: "null_rate_spike",
          severity: "high",
          detected_at: "2026-04-21T00:00:00Z",
          status: "open",
          diagnostics: { reason: "spike" },
          metrics: { null_rate: 0.6 },
          sample_urls: ["https://example.test/artists/a"],
          proposed_action: "Generate remap draft",
          resolution_notes: null,
        },
      ],
    } as never);
    vi.mocked(api.detectSourceDriftSignals).mockResolvedValue({ created: 1, mapping_health: "warning" } as never);
    vi.mocked(api.acknowledgeDriftSignal).mockResolvedValue({ status: "acknowledged" } as never);
    vi.mocked(api.dismissDriftSignal).mockResolvedValue({ status: "dismissed" } as never);
    vi.mocked(api.createRemapDraftFromDriftSignal).mockResolvedValue({
      source_id: "src-1",
      signal_id: "sig-1",
      draft_mapping_version_id: "draft-2",
      based_on_mapping_version_id: "map-1",
      status: "draft_created",
    } as never);
  });

  it("renders drift signal rows", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("null_rate_spike")).toBeInTheDocument());
    expect(screen.getByText("warning")).toBeInTheDocument();
  });

  it("acknowledges a signal", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Acknowledge" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => expect(api.acknowledgeDriftSignal).toHaveBeenCalledWith("src-1", "sig-1"));
  });
});
