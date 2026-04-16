# Backend Runtime Spec

## Goal

Decouple the core crawl/extract runtime from mandatory OpenAI usage.

## Required design changes

### 1. OpenAI must become optional in runtime
The runtime should support:
- `ai_client=None`
- deterministic crawl/extract when runtime rules exist
- clear error only when a job explicitly needs AI and none is available

### 2. Startup/config validation
Current production config should not hard-fail solely because `OPENAI_API_KEY` is absent.

Replace the current behavior with something like:
- OpenAI key required only if AI-assisted features are enabled/needed
- deterministic-only deployments are allowed

## Suggested settings
Add or refine settings such as:
- `OPENAI_REQUIRED=false`
- `CRAWLER_ALLOW_AI=true|false`
- `CRAWLER_REQUIRE_RUNTIME_MAP=true|false`

### 3. PipelineRunner must accept optional AI
Refactor `PipelineRunner` and worker bootstrapping so:
- `ai_client` can be `None`
- AI-only methods validate AI availability explicitly
- deterministic methods do not require AI objects to exist

## Required runtime logic

### Runtime decision flow
At job start:

1. load source
2. determine whether source has a usable runtime map
3. if yes:
   - run deterministic crawl/extract path
   - do not call AI mapping
4. if no:
   - if AI available and allowed, run AI mapping
   - else fail clearly

## Required helper
Add something like:
- `has_usable_runtime_map(source) -> bool`
- `load_runtime_map_for_source(source) -> dict | None`

A “usable runtime map” should mean there are enough rules for:
- page classification
- crawl expansion
- deterministic extraction

## Acceptance criteria
- worker can run without OpenAI in deterministic mode
- pipeline does not instantiate/use AI unnecessarily
- jobs fail clearly only when AI is truly required and unavailable
