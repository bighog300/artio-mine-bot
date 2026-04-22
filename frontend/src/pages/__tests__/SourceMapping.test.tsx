import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "@/components/ui";
import { SourceMapping } from "@/pages/SourceMapping";
import * as api from "@/lib/api";

vi.mock("@/lib/mobile-utils", () => ({ useIsMobile: () => false }));

vi.mock("@/components/source-mapper/PageTypeSidebar", () => ({ PageTypeSidebar: () => <div>PageTypeSidebar</div> }));
vi.mock("@/components/source-mapper/MappingPreviewPanel", () => ({ MappingPreviewPanel: () => <div>MappingPreviewPanel</div> }));
vi.mock("@/components/source-mapper/MappingPresetPanel", () => ({ MappingPresetPanel: () => <div>MappingPresetPanel</div> }));
vi.mock("@/components/source-mapper/MappingMatrix", () => ({ MappingMatrix: () => <div>MappingMatrix</div> }));
vi.mock("@/components/source-mapper/CreatePresetDialog", () => ({ CreatePresetDialog: () => null }));

vi.mock("@/components/source-mapper/ScanSetupForm", () => ({
  ScanSetupForm: ({ runScanDisabledReason }: { runScanDisabledReason?: string | null }) => (
    <div>
      <div>ScanSetupForm</div>
      {runScanDisabledReason ? <div>{runScanDisabledReason}</div> : null}
    </div>
  ),
}));

vi.mock("@/components/source-mapper/SampleRunReview", () => ({
  SampleRunReview: ({ disabledReason }: { disabledReason?: string | null }) => (
    <div>{disabledReason ? `Sample disabled: ${disabledReason}` : "Sample enabled"}</div>
  ),
}));

vi.mock("@/components/source-mapper/VersionHistoryPanel", () => ({
  VersionHistoryPanel: ({ publishDisabledReason, readinessSummary }: { publishDisabledReason?: string | null; readinessSummary?: string | null }) => (
    <div>
      <div>{publishDisabledReason ? `Publish disabled: ${publishDisabledReason}` : "Publish enabled"}</div>
      {readinessSummary ? <div>{readinessSummary}</div> : null}
    </div>
  ),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getSource: vi.fn(),
    getSourceMappingDraft: vi.fn(),
    getSourceMappingRows: vi.fn(),
    getSourceMappingPageTypes: vi.fn(),
    getSourceMappingPreview: vi.fn(),
    getSourceMappingVersions: vi.fn(),
    getSourceMappingDiff: vi.fn(),
    getSourceMappingPresets: vi.fn(),
    getSourceMappingSampleRun: vi.fn(),
    getSourceRuntimeMap: vi.fn(),
    listMappingTemplates: vi.fn(),
    importMappingTemplateFromText: vi.fn(),
    importMappingTemplateFromFile: vi.fn(),
    applyMappingTemplateToSource: vi.fn(),
    exportSourceMappingPreset: vi.fn(),
    createSourceMappingDraft: vi.fn(),
    startSourceMappingScan: vi.fn(),
    updateSourceMappingRow: vi.fn(),
    applySourceMappingAction: vi.fn(),
    startSourceMappingSampleRun: vi.fn(),
    publishSourceMappingDraft: vi.fn(),
    updateSourceMappingSampleRunResult: vi.fn(),
    rollbackSourceMappingVersion: vi.fn(),
    createSourceMappingPreset: vi.fn(),
    deleteSourceMappingPreset: vi.fn(),
    applySourceMappingPreset: vi.fn(),
    startMining: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={["/sources/source-1/mapping?draft=draft-1"]}>
          <Routes>
            <Route path="/sources/:id/mapping" element={<SourceMapping />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}

describe("SourceMapping workflow gating", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSource).mockResolvedValue({
      id: "source-1",
      url: "https://example.com",
      name: "Example",
      status: "idle",
      total_pages: 0,
      total_records: 0,
      last_crawled_at: null,
      created_at: "2026-04-10T00:00:00Z",
      active_mapping_preset_id: null,
      published_mapping_version_id: "version-1",
    });
    vi.mocked(api.getSourceMappingDraft).mockResolvedValue({
      id: "draft-1",
      source_id: "source-1",
      version_number: 2,
      status: "draft",
      scan_status: "completed",
      page_type_count: 1,
      mapping_count: 2,
      approved_count: 1,
      needs_review_count: 1,
      changed_from_published_count: 0,
      scan_progress_percent: 100,
      scan_stage: "done",
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    });
    vi.mocked(api.getSourceMappingRows).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 100 });
    vi.mocked(api.getSourceMappingPageTypes).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 100 });
    vi.mocked(api.getSourceMappingPreview).mockResolvedValue({
      sample_page_id: "sample-1",
      page_url: "https://example.com/page",
      page_type_key: "event_detail",
      extractions: [],
      record_preview: {},
      source_snippet: null,
      category_preview: {},
      warnings: [],
      page_family: {},
      field_sources: {},
      linked_images: [],
      discarded_images: [],
    });
    vi.mocked(api.getSourceMappingVersions).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 });
    vi.mocked(api.getSourceMappingDiff).mockResolvedValue({ added: 0, changed: 0, removed: 0, unchanged: 0 });
    vi.mocked(api.getSourceMappingPresets).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(api.getSourceRuntimeMap).mockResolvedValue({
      source_id: "source-1",
      runtime_map_source: "source_structure_map",
      active_mapping_preset_id: null,
      runtime_mapping_updated_at: null,
      runtime_map: { crawl_plan: { phases: [{ name: "seed" }] } },
    });
    vi.mocked(api.listMappingTemplates).mockResolvedValue({ items: [], total: 0 });
  });

  it("disables start mining when runtime map has no extraction payload", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Runtime mapping has no extraction/mining rules.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Start Mining" })).toBeDisabled();
    });
  });

  it("shows guided next-step and disabled reasons for sample and publish", async () => {
    vi.mocked(api.getSourceMappingDraft).mockResolvedValueOnce({
      id: "draft-1",
      source_id: "source-1",
      version_number: 2,
      status: "draft",
      scan_status: "running",
      page_type_count: 1,
      mapping_count: 2,
      approved_count: 0,
      needs_review_count: 2,
      changed_from_published_count: 0,
      scan_progress_percent: 60,
      scan_stage: "classify",
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Next step: wait for scan completion and then review rows.")).toBeInTheDocument();
      expect(screen.getByText("Sample disabled: Complete scan before running sample extraction.")).toBeInTheDocument();
      expect(screen.getByText("Publish disabled: Complete scan before publishing.")).toBeInTheDocument();
    });
  });
});
