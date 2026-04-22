import { useState } from "react";

import type { MappingTemplate, SourceMappingPreset } from "@/lib/api";

interface Props {
  presets: SourceMappingPreset[];
  loading: boolean;
  deletingPresetId: string | null;
  applyingPresetId: string | null;
  templates: MappingTemplate[];
  templatesLoading: boolean;
  applyingTemplateId: string | null;
  onOpenCreate: () => void;
  onDelete: (presetId: string) => void;
  onApply: (presetId: string) => void;
  onExport: (presetId: string) => void;
  onImportText: (payload: { name: string; description?: string; content: string }) => void;
  onImportFile: (payload: { name: string; description?: string; file: File }) => void;
  onApplyTemplate: (templateId: string) => void;
  canCreate: boolean;
}

export function MappingPresetPanel({
  presets,
  loading,
  deletingPresetId,
  applyingPresetId,
  templates,
  templatesLoading,
  applyingTemplateId,
  onOpenCreate,
  onDelete,
  onApply,
  onExport,
  onImportText,
  onImportFile,
  onApplyTemplate,
  canCreate,
}: Props) {
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [templateContent, setTemplateContent] = useState("");

  return (
    <section className="rounded border bg-card p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Mapping Presets</h2>
        <button className="px-3 py-1 rounded bg-foreground text-white text-sm disabled:opacity-60" onClick={onOpenCreate} disabled={!canCreate}>Save as Preset</button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading presets...</p>
      ) : presets.length === 0 ? (
        <p className="text-sm text-muted-foreground">No presets yet for this source.</p>
      ) : (
        <ul className="space-y-2">
          {presets.map((preset) => (
            <li key={preset.id} className="rounded border p-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{preset.name}</div>
                  {preset.description ? <div className="text-xs text-muted-foreground">{preset.description}</div> : null}
                  <div className="mt-1 text-xs text-muted-foreground">
                    Rows: <strong>{preset.row_count}</strong> · Page types: <strong>{preset.page_type_count}</strong>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {preset.created_from_mapping_version_id ? `From version: ${preset.created_from_mapping_version_id}` : "From current draft"} · Created {new Date(preset.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="px-2 py-1 border rounded text-xs" onClick={() => onExport(preset.id)}>Export</button>
                  <button
                    className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    onClick={() => onApply(preset.id)}
                    disabled={applyingPresetId === preset.id}
                  >
                    {applyingPresetId === preset.id ? "Applying..." : "Apply"}
                  </button>
                  <button
                    className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                    onClick={() => onDelete(preset.id)}
                    disabled={deletingPresetId === preset.id}
                  >
                    {deletingPresetId === preset.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="border-t pt-3 space-y-2">
        <h3 className="text-sm font-semibold">External Templates</h3>
        <input className="w-full rounded border px-2 py-1 text-sm" placeholder="Template name" value={templateName} onChange={(e) => setTemplateName(e.target.value)} />
        <input className="w-full rounded border px-2 py-1 text-sm" placeholder="Description (optional)" value={templateDescription} onChange={(e) => setTemplateDescription(e.target.value)} />
        <textarea className="w-full rounded border px-2 py-1 text-xs min-h-28" placeholder="Paste template JSON here" value={templateContent} onChange={(e) => setTemplateContent(e.target.value)} />
        <div className="flex items-center gap-2">
          <button
            className="px-2 py-1 border rounded text-xs disabled:opacity-60"
            disabled={!templateName.trim() || !templateContent.trim()}
            onClick={() => onImportText({ name: templateName.trim(), description: templateDescription.trim() || undefined, content: templateContent })}
          >
            Save from text
          </button>
          <input
            aria-label="template-file-input"
            type="file"
            accept="application/json"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file || !templateName.trim()) return;
              onImportFile({ name: templateName.trim(), description: templateDescription.trim() || undefined, file });
              e.currentTarget.value = "";
            }}
          />
        </div>

        {templatesLoading ? (
          <p className="text-xs text-muted-foreground">Loading templates...</p>
        ) : templates.length === 0 ? (
          <p className="text-xs text-muted-foreground">No external templates yet.</p>
        ) : (
          <ul className="space-y-1">
            {templates.map((template) => (
              <li key={template.id} className="border rounded p-2 text-xs flex items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{template.name}</div>
                  <div className="text-muted-foreground">Schema v{template.schema_version}</div>
                </div>
                <button
                  className="px-2 py-1 border rounded text-xs disabled:opacity-60"
                  onClick={() => onApplyTemplate(template.id)}
                  disabled={applyingTemplateId === template.id}
                >
                  {applyingTemplateId === template.id ? "Applying..." : "Apply to source"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
