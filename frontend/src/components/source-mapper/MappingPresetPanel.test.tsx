import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MappingPresetPanel } from "@/components/source-mapper/MappingPresetPanel";

describe("MappingPresetPanel", () => {
  it("supports export and template import/apply actions", async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    const onImportText = vi.fn();
    const onApplyTemplate = vi.fn();

    render(
      <MappingPresetPanel
        presets={[
          {
            id: "preset-1",
            name: "Preset 1",
            description: null,
            created_from_mapping_version_id: null,
            row_count: 2,
            page_type_count: 1,
            created_at: "2026-04-22T00:00:00Z",
            updated_at: "2026-04-22T00:00:00Z",
          },
        ]}
        loading={false}
        deletingPresetId={null}
        applyingPresetId={null}
        templates={[
          {
            id: "template-1",
            name: "Portable",
            description: null,
            schema_version: 1,
            is_system: false,
            created_by: "admin",
            created_at: "2026-04-22T00:00:00Z",
            updated_at: "2026-04-22T00:00:00Z",
          },
        ]}
        templatesLoading={false}
        applyingTemplateId={null}
        onOpenCreate={vi.fn()}
        onDelete={vi.fn()}
        onApply={vi.fn()}
        onExport={onExport}
        onImportText={onImportText}
        onImportFile={vi.fn()}
        onApplyTemplate={onApplyTemplate}
        canCreate
      />
    );

    await user.click(screen.getByRole("button", { name: "Export" }));
    expect(onExport).toHaveBeenCalledWith("preset-1");

    await user.type(screen.getByPlaceholderText("Template name"), "Imported Template");
    fireEvent.change(screen.getByPlaceholderText("Paste template JSON here"), {
      target: {
        value:
          '{"payload":{"crawl_plan":{"phases":[{"phase_name":"root"}]},"extraction_rules":{"event":{"css_selectors":{"title":".title"}}}}}',
      },
    });
    await user.click(screen.getByRole("button", { name: "Save from text" }));

    expect(onImportText).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Imported Template" })
    );

    await user.click(screen.getByRole("button", { name: "Apply to source" }));
    expect(onApplyTemplate).toHaveBeenCalledWith("template-1");
  });
});
