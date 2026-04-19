You are implementing a retrofit in this repository.

Your mission is to change the system from mixed AI/deterministic mining to **one-time AI discovery + zero-AI runtime mining**.

Read these repo documents first and treat them as the instructions for this task:
1. `AGENTS.md`
2. `docs/runtime-zero-ai/ARCHITECTURE.md`
3. `docs/runtime-zero-ai/IMPLEMENTATION_PLAN.md`
4. `docs/runtime-zero-ai/TASK_BREAKDOWN.md`
5. `docs/runtime-zero-ai/ACCEPTANCE_CRITERIA.md`

Important repo note:
- The old repository `AGENTS.md` may describe the original scaffold/build flow for the project and is stale for this task.
- Follow the bundled `AGENTS.md` for this implementation.

Outcome required:
- when a source is first created, discovery may use AI to map the site and propose what to mine
- discovery persists a draft mapping and allows publishing a runtime mapping
- once a runtime mapping is published, all normal crawl/mining/enrichment jobs for that source must use **zero AI tokens**
- runtime must classify and extract deterministically from the published mapping only
- runtime failures must queue review/remapping states instead of falling back to AI
- unchanged pages should be skipped via content hash
- mapping drift should mark the source stale without triggering runtime AI use

Guardrails:
- do not leave any runtime AI fallback in place for published sources
- fail closed if a published-source runtime flow tries to call AI
- keep changes incremental and test-backed
- prefer using the deterministic crawler/runtime path as the primary executor for published sources
- confine legacy AI classifier/extractors to discovery/remapping/manual explicit repair flows only

Execution sequence:
1. inspect current models, pipeline runner, crawler, discovery/site-mapping modules, and AI call sites
2. implement schema and mapping lifecycle changes
3. add runtime AI policy enforcement
4. route published-source runtime jobs through deterministic execution
5. add content-hash skip behavior
6. replace runtime AI fallback with review states
7. add drift detection and stale mapping state
8. add/update tests proving zero runtime AI calls
9. update docs if needed

Definition of done:
- published-source runtime crawl repeatedly runs with zero OpenAI calls
- review/remap states appear instead of runtime AI fallback
- tests cover policy, mapping lifecycle, runtime path, skip logic, and drift signals

When coding:
- inspect existing callers before changing behavior
- make small coherent commits
- include concise structured logs around policy decisions
- keep migrations explicit
