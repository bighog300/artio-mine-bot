# Sprint 1: Directory & Deep Extraction Architecture

## Objective
Enable the miner to correctly identify directory pages, artist hub pages, and automatically deepen into structured child pages.

## Scope
- Add new page types
- Fix classifier misclassification
- Implement discovery vs extraction separation
- Add directory expansion logic
- Add deepen_same_slug_children()
- Update pipeline runner
- Add tests

## Acceptance Criteria
- Directory pages expand into artist pages
- Artist hubs trigger deep extraction
- Child pages are fetched
- Tests pass
