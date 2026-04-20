# CODEX_EXECUTION_PROMPT

You are implementing the Artio creator-facing UX upgrade in an existing codebase.

## Mission
Build the creator experience after the user phase is complete. Focus on artists and venue owners who want to:
- publish events
- publish galleries
- preview content before going live
- manage their public Artio space
- see basic performance feedback

Do not work on admin/moderation surfaces.

## Constraints
- Preserve existing architecture conventions, routing, state management, styling, and API patterns
- Reuse existing forms, media, and dashboard primitives where available
- Keep creator-specific code isolated from general user browsing code where practical
- Maintain accessibility and responsive behavior
- Leave admin surfaces untouched

## Required reading order
1. SCREEN_MAP.md
2. DATA_MODEL.md
3. API_CONTRACTS.md
4. ANALYTICS_EVENTS.md
5. ACCEPTANCE_CRITERIA.md
6. IMPLEMENTATION_PLAN.md

## Preconditions
- The user-facing phase has already been implemented or at least the shared published entities (event/gallery/creator) exist
- Reuse shared event/gallery models when publishing content

## Phase 1 tasks
1. Audit the repo and identify existing creator, profile, dashboard, media, and publishing capabilities
2. Produce a gap list mapped to the acceptance criteria
3. Implement creator account/profile basics
4. Implement creator onboarding
5. Implement dashboard with drafts, upcoming content, and quick create actions
6. Implement event draft creation/editing with a stepper flow and preview
7. Implement gallery draft creation/editing with a stepper flow and preview
8. Implement media upload and selection abstraction
9. Implement publish actions and content state badges
10. Implement a basic public page configuration flow
11. Implement creator analytics summary view
12. Validate against every Phase 1 acceptance criterion and note blockers

## Phase 2 tasks
1. Add scheduled publishing for events and galleries
2. Add resumable drafts and stronger field-level validation
3. Add public page section ordering and featured content controls
4. Expand analytics by date range and top-performing content
5. Refine venue-owner-specific fields and section behavior
6. Validate against every Phase 2 acceptance criterion

## Working style
- Start by documenting current-state findings in a markdown file named CREATOR_IMPLEMENTATION_AUDIT.md
- Then create a phased task checklist named CREATOR_EXECUTION_CHECKLIST.md
- Implement in small logical commits or commit-like sections
- Prefer a robust but minimal MVP before advanced customization
- If the repository is frontend-only, create typed service interfaces and mock adapters behind clean boundaries
- If the repository is backend-only, implement APIs and example payloads plus concise usage documentation

## Definition of done
- Creator onboarding, dashboard, draft flows, preview, publish, public page basics, and analytics summary are functional
- Scheduled publishing and public page customization improvements are integrated in Phase 2
- Acceptance criteria are checked off with notes
- No admin surfaces are changed
