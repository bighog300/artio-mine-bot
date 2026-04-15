import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MappingMatrix } from "@/components/source-mapper/MappingMatrix";
import { MappingPreviewPanel } from "@/components/source-mapper/MappingPreviewPanel";
import { SampleRunReview } from "@/components/source-mapper/SampleRunReview";
import { VersionHistoryPanel } from "@/components/source-mapper/VersionHistoryPanel";
import type {
  MappingDiffSummary,
  MappingPreviewResponse,
  MappingRow,
  MappingSampleRunResultResponse,
  MappingVersion,
} from "@/lib/api";

describe("Source mapper critical flows", () => {
  it("supports mapping row inline edits", async () => {
    const user = userEvent.setup();
    const onRowUpdate = vi.fn();
    const row: MappingRow = {
      id: "row-1",
      mapping_version_id: "draft-1",
      page_type_id: "page-type-1",
      selector: ".event-title",
      extraction_mode: "text",
      sample_value: "Open Studio",
      destination_entity: "event",
      destination_field: "title",
      category_target: null,
      confidence_score: 0.82,
      status: "proposed",
      is_required: false,
      is_enabled: true,
      sort_order: 1,
      transforms: [],
      rationale: [],
      confidence_band: "HIGH",
      low_confidence_blocked: false,
    };

    render(
      <MappingMatrix
        rows={[row]}
        statusFilter="all"
        onStatusFilterChange={vi.fn()}
        selectedRowIds={[]}
        setSelectedRowIds={vi.fn()}
        onRowUpdate={onRowUpdate}
      />
    );

    const destinationSelect = screen.getAllByRole("combobox")[1];
    await user.selectOptions(destinationSelect, "artist");
    expect(onRowUpdate).toHaveBeenCalledWith(
      "row-1",
      expect.objectContaining({ destination_entity: "artist", destination_field: "title", status: "needs_review" })
    );

    const categoryInput = screen.getByPlaceholderText("taxonomy/category");
    await user.type(categoryInput, "contemporary");
    await user.tab();
    expect(onRowUpdate).toHaveBeenCalledWith("row-1", { category_target: "contemporary", status: "needs_review" });
  });

  it("renders preview panel details and warnings", () => {
    const preview: MappingPreviewResponse = {
      sample_page_id: "sample-1",
      page_url: "https://example.com/event/1",
      page_type_key: "event_detail",
      source_snippet: "<h1>Open Studio</h1>",
      extractions: [
        {
          mapping_row_id: "row-1",
          source_selector: ".event-title",
          raw_value: "Open Studio",
          normalized_value: "Open Studio",
          destination_entity: "event",
          destination_field: "title",
          category_target: null,
          confidence_score: 0.88,
          warning: null,
        },
      ],
      record_preview: { title: "Open Studio" },
      category_preview: { themes: ["studio"] },
      warnings: ["Missing timezone"],
    };

    render(<MappingPreviewPanel preview={preview} />);

    expect(screen.getByText("https://example.com/event/1")).toBeInTheDocument();
    expect(screen.getByText("event.title")).toBeInTheDocument();
    expect(screen.getByText("Missing timezone")).toBeInTheDocument();
  });

  it("sends moderation updates from sample-run controls", async () => {
    const user = userEvent.setup();
    const onModerateResult = vi.fn();
    const sampleRun: MappingSampleRunResultResponse = {
      sample_run_id: "run-1",
      status: "completed",
      items: [
        {
          id: "result-1",
          sample_run_id: "run-1",
          sample_id: "sample-1",
          review_status: "needs_review",
          review_notes: "Initial note",
          record_preview: { title: "Open Studio" },
          created_at: "2026-04-15T00:00:00Z",
          updated_at: "2026-04-15T00:00:00Z",
        },
      ],
    };

    render(
      <SampleRunReview sampleRun={sampleRun} onStart={vi.fn()} loading={false} onModerateResult={onModerateResult} />
    );

    await user.click(screen.getByRole("button", { name: "Approve" }));
    expect(onModerateResult).toHaveBeenCalledWith("result-1", { review_status: "approved" });

    const notesInput = screen.getByPlaceholderText("Optional moderation notes");
    await user.clear(notesInput);
    await user.type(notesInput, "Looks good");
    await user.tab();
    expect(onModerateResult).toHaveBeenCalledWith("result-1", { review_notes: "Looks good" });
  });

  it("exposes publish and rollback controls", async () => {
    const user = userEvent.setup();
    const onPublish = vi.fn();
    const onRollback = vi.fn();
    const versions: MappingVersion[] = [
      {
        id: "v1",
        source_id: "source-1",
        version_number: 1,
        status: "published",
        scan_status: "completed",
        created_at: "2026-04-14T00:00:00Z",
        updated_at: "2026-04-14T00:00:00Z",
        published_at: "2026-04-14T01:00:00Z",
        created_by: "admin",
        published_by: "admin",
      },
    ];
    const diff: MappingDiffSummary = { added: 1, removed: 0, changed: 2, unchanged: 4 };

    render(
      <VersionHistoryPanel versions={versions} diff={diff} onPublish={onPublish} publishing={false} onRollback={onRollback} />
    );

    await user.click(screen.getByRole("button", { name: "Publish Draft" }));
    expect(onPublish).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Rollback" }));
    expect(onRollback).toHaveBeenCalledWith("v1");
  });
});
