# Codex Implementation Brief

Implement preset-driven mining and enrichment for existing sources.

Required outcomes:
- existing sources with applied preset/runtime map can mine deterministically
- enrichment-only runs can operate on stored pages/content
- presets influence crawl behavior, not just extraction selectors
- deterministic runs capture/link media and improve entity completeness
- operators can explicitly run mining vs enrichment and see meaningful progress

Constraints:
- reuse existing FastAPI / SQLAlchemy / Alembic / React patterns
- keep changes incremental
- preserve AI-assisted mode for explicit refresh/improvement workflows
- avoid unrelated refactors

Definition of done:
- known sources can be mined and enriched from saved runtime config
- enrichment improves existing records without full recrawl
- operator controls/metrics clearly distinguish mining and enrichment outcomes
