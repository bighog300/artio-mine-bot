# Frontend Spec

## New Page
- /sources/:id/operations

## Layout
Header:
- Source name, status, active jobs, pending moderation

Left:
- Action controls
- Moderation queue

Right:
- Live console (SSE)

Bottom:
- Run history

## Components
- SourceOperationsHeader
- SourceActionPanel
- ModeratedActionQueue
- SourceLiveConsole
- SourceRunHistory

## Console Modes
- Active job only
- Full source stream
- Moderation events
