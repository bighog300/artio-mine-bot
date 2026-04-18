# Durable Crawler Consolidation & Prioritization – Implementation Checklist

## Epic: Consolidate crawler into a compliant, priority-aware durable frontier

---

## Milestone 1: Robots Compliance

### CRAWL-101 — Add robots checks to durable frontier
- [ ] Integrate RobotsChecker into durable_frontier
- [ ] Skip disallowed URLs before fetch
- [ ] Mark status as `skipped` with reason `robots_blocked`
- [ ] Emit crawl events for blocked URLs

### CRAWL-102 — Add robots-aware stats
- [ ] Track `robots_blocked_count`
- [ ] Expose in API/reporting

### CRAWL-103 — Add tests
- [ ] Allowed URL fetch test
- [ ] Blocked URL skip test
- [ ] Retry prevention test
- [ ] Robots caching test

---

## Milestone 2: Single Crawl Engine

### CRAWL-201 — Declare durable frontier canonical
- [ ] Mark link_follower deprecated
- [ ] Update docs

### CRAWL-202 — Extract seeding module
- [ ] Create `app/crawler/seeding.py`
- [ ] Move root + structure seeding logic

### CRAWL-203 — Route all callers
- [ ] Replace crawl_source calls
- [ ] Use durable frontier everywhere

### CRAWL-204 — Migrate tests
- [ ] Remove legacy assumptions
- [ ] Align with durable frontier behavior

### CRAWL-205 — Remove link_follower
- [ ] Delete queue logic
- [ ] Clean imports/tests

---

## Milestone 3: Priority-Aware Crawling

### CRAWL-301 — Add frontier metadata
- [ ] Add priority column
- [ ] Add predicted_page_type
- [ ] Add migration

### CRAWL-302 — Priority-based claiming
- [ ] Sort by priority > depth > age

### CRAWL-303 — Crawl policy module
- [ ] Create `crawl_policy.py`
- [ ] Implement URL scoring
- [ ] Add heuristics + structure map support

### CRAWL-304 — Score links before enqueue
- [ ] Apply scoring on discovery
- [ ] Persist metadata

### CRAWL-305 — Post-fetch refinement
- [ ] Infer page_type from HTML
- [ ] Store on pages

### CRAWL-306 — Follow-policy hints
- [ ] Use structure map follow rules
- [ ] Boost/deprioritize links

### CRAWL-307 — Crawl-order tests
- [ ] Validate prioritization works
- [ ] Ensure fallback behavior

---

## Optional

### CRAWL-401 — Exploration budget
- [ ] Reserve % for low-priority URLs

### CRAWL-402 — Debug visibility
- [ ] Show priority/page type in admin UI

---

## Labels
- crawler
- backend
- migration
- tech-debt
- high-priority
- testing
- architecture
