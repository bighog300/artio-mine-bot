# Codex Implementation Brief

Implement Source Operations Console per spec.

Requirements:
- Source-level control endpoints
- Source-level event streaming
- Moderation queue UI + API
- Live console (SSE)
- Run history UI

Constraints:
- Reuse existing job + SSE systems
- Minimal refactor
- Production-ready behavior

Definition of Done:
- Operator can monitor all activity for a source
- Live log console works
- Moderation actions visible and actionable
- Runs history visible
