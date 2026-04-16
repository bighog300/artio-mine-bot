# Source Mapper — Known Issues and Guardrails

These findings were identified during audit and should inform implementation.

## Current issues worth noting

### 1. Mapping scan route looks asynchronous but behaves synchronously
The scan endpoint returns a `202`-style response with a pseudo job identifier, but runs the scan inline.
Do not depend on this route being a true queued job unless you explicitly refactor it.

### 2. Draft creation may trigger scan inline
Draft creation can unexpectedly do more work than its name suggests.
Preset creation should not add more hidden long-running behavior.

### 3. Mapping row pagination total is inaccurate
Existing row list logic may report `total=len(items)` for the current page rather than the full filtered count.
Do not copy that pattern into preset listing.

### 4. Bulk approval validation is too broad
Some approval validation appears to query broadly rather than by exact selected IDs.
Preset creation should use explicit origin/version filters and explicit row selection logic.

## Guardrails for preset work

- keep preset creation explicit and synchronous unless intentionally jobified
- do not couple preset rows back to live draft rows after creation
- do not silently include rejected/low-confidence rows unless requested
- do not implement preset apply/import in this scope
