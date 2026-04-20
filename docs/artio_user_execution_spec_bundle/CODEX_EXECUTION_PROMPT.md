# CODEX_EXECUTION_PROMPT

You are implementing the Artio user-facing UX upgrade in an existing codebase.

## Mission
Build the user experience in two sequential phases. Do not work on admin surfaces. Do not build creator publishing tools in this phase. Focus only on the basic explorer user who wants to:
- be notified about events
- browse events and galleries
- save content
- follow creators/venues
- receive useful recommendations

## Constraints
- Preserve existing architecture conventions, routing, state management, styling, and API patterns
- Reuse existing components when possible
- Keep changes production-oriented, not demo-only
- Favor incremental PR-ready work over speculative rewrites
- Maintain accessibility and responsive behavior
- If the repository already contains overlapping features, refactor carefully instead of duplicating
- Leave admin surfaces untouched

## Required reading order
1. SCREEN_MAP.md
2. DATA_MODEL.md
3. API_CONTRACTS.md
4. RECOMMENDATION_RULES.md
5. NOTIFICATION_RULES.md
6. ANALYTICS_EVENTS.md
7. ACCEPTANCE_CRITERIA.md
8. IMPLEMENTATION_PLAN.md

## Phase 1 tasks
1. Audit the repo and identify existing user-facing surfaces relevant to explore, events, galleries, saved items, notifications, and profile/preferences
2. Produce a gap list mapped to the acceptance criteria
3. Implement or adapt the data structures and APIs required for:
   - user interests
   - notification preferences
   - saves
   - follows
   - reminders
   - notifications
4. Implement the user UI surfaces:
   - onboarding
   - explore
   - events list
   - event detail
   - galleries list
   - gallery detail
   - saved
   - notification inbox
5. Add one-tap save and follow interactions
6. Add event reminder creation/deletion with 2h and 24h presets minimum
7. Implement deterministic explore ranking and mixed feed assembly per RECOMMENDATION_RULES.md
8. Add analytics event instrumentation for all phase 1 flows
9. Validate against every Phase 1 acceptance criterion and list anything blocked by repository limitations

## Phase 2 tasks
1. Add behavior-based recommendation inputs
2. Add recommendation rails:
   - New from followed creators
   - Trending near you
3. Add ranking reason plumbing in API payloads and UI where appropriate
4. Add quiet hours and frequency caps to recommendation notifications
5. Improve search across events, galleries, creators, and venues
6. Expand analytics instrumentation for retention loops
7. Validate against every Phase 2 acceptance criterion

## Working style
- Start by documenting current-state findings in a markdown file named IMPLEMENTATION_AUDIT.md
- Then create a phased task checklist named EXECUTION_CHECKLIST.md
- Implement in small logical commits or commit-like sections
- Where the spec leaves room for judgment, choose the simplest robust implementation
- If backend pieces are missing and the repo is frontend-only, create typed service interfaces and realistic mocks behind a clear abstraction
- If frontend pieces are missing and the repo is backend-only, implement APIs and example payloads plus brief usage docs

## Definition of done
- Phase 1 user flows work end-to-end in the current environment
- Phase 2 recommendation and notification improvements are integrated
- Acceptance criteria are checked off with notes
- No admin surfaces are changed
