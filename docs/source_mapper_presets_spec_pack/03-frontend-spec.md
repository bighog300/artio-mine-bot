# Source Mapper Presets — Frontend Spec

## Goal

Give operators simple UI controls to save mapper findings as presets and delete them later.

## Target page

Extend the existing source mapper UI, likely the current source mapping page, rather than creating a new standalone page.

## Required UI additions

### Presets panel

Add a panel or section to the mapper page showing:
- preset name
- description
- created date
- row count
- origin version if available
- delete action

### Save as Preset action

Add a button such as:
- `Save as Preset`

Clicking it opens a modal/dialog with:

- preset name
- description optional
- source draft/version reference shown read-only
- checkbox or selector for included statuses
  - default: approved only

On submit:
- call create preset API
- refresh preset list
- show success/error feedback

### Delete Preset action

Each preset row/card should provide:
- delete button
- confirmation prompt/modal

On confirm:
- call delete preset API
- refresh list
- show success/error feedback

## API client additions

Add frontend API methods for:
- `getSourceMappingPresets(sourceId)`
- `createSourceMappingPreset(sourceId, payload)`
- `deleteSourceMappingPreset(sourceId, presetId)`

## Suggested components

Add or extend components like:
- `MappingPresetPanel.tsx`
- `CreatePresetDialog.tsx`

Reuse existing modal, table, button, toast, and loading state patterns in the repo.

## UX behavior

- Disable create action while request is in flight
- Show empty state when no presets exist
- Show clear validation errors from backend
- Keep the flow lightweight; v1 does not need editing or applying presets

## V1 acceptance

Operator can:
- save findings from a draft/version as a preset
- see saved presets for the source
- delete a preset
