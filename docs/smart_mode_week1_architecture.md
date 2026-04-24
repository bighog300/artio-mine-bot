# Smart Mode Week 1 Architecture

## Components

- `app/ai/openai_client.py`: Async OpenAI wrapper with JSON mode, retries, and usage/cost tracking.
- `app/ai/site_analyzer.py`: Uses GPT-3.5 model to classify site type/CMS/entity patterns.
- `app/ai/config_generator.py`: Uses GPT-4o to generate runtime mining config and validates it.
- `app/ai/quality_assurance.py`: Runs mini crawl tests and refines config when success rate is low.
- `app/ai/smart_miner.py`: Orchestrates end-to-end smart mining workflow and saves `structure_map`.
- `app/ai/models.py`: Pydantic models for smart mode outputs.

## Workflow

1. Analyze site (`analyzing`).
2. Generate config (`generating_config`).
3. QA mini crawl (`testing`) with optional refinement.
4. Save configuration and transition to `mining`.

## Notes

- OpenAI usage and cost totals are tracked per model and aggregated.
- Generated configurations are checked against existing template validation rules and strict identifier/selector rules.
- QA creates and deletes temporary sources in a `try/finally` block.
