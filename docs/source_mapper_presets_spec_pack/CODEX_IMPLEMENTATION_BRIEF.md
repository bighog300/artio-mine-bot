# Codex Implementation Brief — Source Mapper Presets

Implement support for:

- preset create
- preset delete
- saving mapper findings as presets

Treat the accompanying markdown documents as the source of truth.

## Scope

Build a minimal, production-ready v1 preset system for the existing AI Source Mapper.

Required:
- backend schema for presets
- migration
- CRUD helpers
- API routes
- frontend preset list
- create preset flow
- delete preset flow

## Important constraints

- reuse the existing source mapper draft/version system
- keep presets source-local in v1
- save copied snapshot rows, not references
- default to approved rows only
- avoid unrelated refactors
- do not implement preset apply/import in this task

## Done when

- operator can create a preset from mapper findings
- preset appears in the source mapper UI
- operator can delete a preset
- backend validates source ownership and row availability
- migration applies cleanly
