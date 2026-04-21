# UI Workflow

## New source onboarding wizard

### Step 1: Enter source
Admin enters:
- seed URL
- optional label/name
- optional crawl scope notes

### Step 2: Profile site
System runs a shallow profile and shows:
- homepage summary
- sitemap detected / not detected
- top URL families
- representative samples

### Step 3: Review families
For each discovered family, show:
- proposed label
- path pattern
- candidate page type
- confidence
- sample URLs
- sample visible fields / extraction preview
- include/exclude toggle
- follow links toggle
- pagination guess

### Step 4: Approve mapping
Admin can:
- rename family
- override page type
- disable family
- adjust follow / pagination mode
- publish as mapping version

### Step 5: Start crawl
Admin can:
- run immediately
- schedule first full crawl
- choose refresh policy

## Resume workflow

For interrupted or paused runs, show:
- run status
- checkpoint timestamp
- frontier counts
- failed URLs
- pending URLs
- resume button
- rerun failed only button

## Drift workflow

Show:
- source with active drift signals
- which families degraded
- what changed
- suggested remap button
- preview of new families or changed samples

## Minimal UI implementation recommendation

Start with:
- source onboarding/profile page
- family review/approval panel
- crawl run resume card
- drift signal list

Do not block implementation on a complex studio.
