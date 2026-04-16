# Codex Implementation Brief

Implement an AI-optional crawler mode.

Required outcomes:
- crawler can run without OpenAI when a usable runtime map exists
- saved presets can be applied to a source and used as runtime configuration
- `run_full_pipeline()` skips AI mapping when runtime map already exists
- deterministic crawl/extract proceeds without crashing when AI is unavailable
- operator can see whether a job is running in deterministic or AI-assisted mode

Constraints:
- reuse existing FastAPI / SQLAlchemy / Alembic / React patterns
- keep the change incremental
- avoid broad unrelated refactors
- preserve AI-assisted mode when runtime map is missing and AI is available

Definition of done:
- OpenAI is optional for deterministic preset-driven runs
- applied presets materially change runtime behavior
- jobs can create records from saved runtime maps without calling OpenAI
