# Implementation Plan

## Phase 1 — Remove mandatory OpenAI dependency
- make config validation OpenAI-optional
- make `OpenAIClient` optional in worker boot path
- allow `PipelineRunner(ai_client=None)`

## Phase 2 — Runtime map detection and flow control
- add `has_usable_runtime_map(...)`
- add `load_runtime_map_for_source(...)`
- change `run_full_pipeline()` to skip AI mapping when runtime map exists

## Phase 3 — Preset application
- add preset apply backend flow
- persist active preset/runtime map on source
- add apply preset route

## Phase 4 — Deterministic crawl/extract path
- use applied runtime map in crawl and extraction
- skip AI fallback when AI unavailable
- emit deterministic hit/miss events

## Phase 5 — Operator visibility
- expose runtime mode and runtime map source
- improve logs/SSE/Job Detail messaging

## Recommended order
1. optional OpenAI runtime
2. skip AI mapping if runtime map exists
3. preset apply -> runtime map
4. deterministic crawl/extract improvements
5. UI visibility
