# MASTER_EXECUTION_PROMPT_FOR_CODEX

Implement the Artio upgrade in two phasesets, in this exact order:

## Phase Set A: User Experience
Use the USER execution spec bundle first.
Goal:
Deliver the explorer-facing experience for event notifications, event discovery, gallery browsing, saves, follows, and recommendations.

Required outcome before moving on:
- Phase 1 and Phase 2 user acceptance criteria are substantially met or any blockers are explicitly documented.

## Phase Set B: Creator Experience
Only after completing Phase Set A, use the CREATOR execution spec bundle.
Goal:
Deliver creator onboarding, publishing flows, preview, public page basics, and analytics.

## Global rules
- Do not edit admin or moderation surfaces
- Reuse shared entities and components where possible
- Avoid parallel speculative rewrites
- Document repo audit findings and blockers
- Maintain testability, accessibility, and responsiveness
- Prefer end-to-end usable flows over incomplete abstractions
