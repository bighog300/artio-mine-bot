# Architecture

## Target architecture

Browser/Admin UI
    -> Mapping approval workflow
    -> Crawl run controls
    -> Frontier / drift diagnostics

API layer
    -> source profiling endpoints
    -> mapping suggestion endpoints
    -> mapping approval endpoints
    -> crawl execution / resume endpoints

Profiling engine
    -> seed sampler
    -> sitemap/nav discovery
    -> URL clustering
    -> structural analysis
    -> page-type candidate inference

Mapping engine
    -> candidate mapping generator
    -> family typing
    -> pagination / follow rules
    -> include/exclude suggestions
    -> LLM ambiguity resolver

Crawl engine
    -> durable frontier
    -> checkpointed crawl run
    -> queue integration
    -> resumable processing
    -> incremental recrawl scheduler

Drift engine
    -> mapping degradation signals
    -> new-family detection
    -> confidence/null-rate tracking
    -> remap suggestions

## Key design principles

### 1. Profile before crawling deeply
Do not start full crawl on an unseen site immediately.
First:
- sample
- cluster
- propose

### 2. Families, not only pages
Treat repeated page structures as first-class objects:
- artist family
- artwork family
- exhibition family
- listing family
- document/PDF family
- generic content family

### 3. Approved mapping versions
Each source should have:
- draft mapping suggestions
- approved active mapping
- version history

### 4. Durable frontier
Each discovered URL should have persistent status and metadata:
- discovered
- queued
- fetched
- extracted
- skipped
- failed
- retryable

### 5. Refresh by policy, not brute force
Use:
- per-family freshness policies
- content hashes
- crawl priority
- change detection

### 6. Drift is normal
Site changes are expected. Build for:
- detection
- proposal
- approval
- migration

## Suggested modules

Adapt to current repo layout where reasonable.

- `app/source_profiler/`
  - `service.py`
  - `discovery.py`
  - `clustering.py`
  - `signals.py`
  - `models.py`

- `app/source_mapper/`
  - extend existing mapper to support candidate families + versioning
  - `suggestions.py`
  - `approval.py`
  - `presets.py`

- `app/crawl_frontier/`
  - `models.py`
  - `service.py`
  - `scheduler.py`
  - `resume.py`

- `app/drift_detection/`
  - `service.py`
  - `signals.py`

- `app/api/routes/`
  - new or extended routes for profiler/mapping/resume/drift

- `frontend/src/pages/`
  - mapping onboarding wizard
  - family review page
  - crawl resume view
  - drift review page
