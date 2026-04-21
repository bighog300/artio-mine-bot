# Drift Detection

## What is drift

Drift means the approved mapping is losing fitness because the source changed.

Examples:
- selectors no longer match
- family structure changed
- page null rates increased sharply
- new URL family emerged
- pagination changed
- listing/detail boundary changed

## Signals to implement first

### High-value initial signals
- null-rate increase for required fields
- extraction confidence drop
- selector miss rate increase
- new recurring path pattern not covered by approved mapping
- sudden rise in skipped pages for one family

### Useful secondary signals
- family sample DOM similarity drift
- image/text ratio changes
- date block disappearance
- canonical URL pattern changes

## Actions on drift

For medium/high severity:
- create drift signal record
- notify admin in UI
- offer “profile family again” or “generate remap draft”

## Mapping versioning policy

Do not mutate the active mapping blindly.

Instead:
- detect drift against active mapping vN
- generate draft mapping vN+1
- admin reviews and approves
- future runs use vN+1
