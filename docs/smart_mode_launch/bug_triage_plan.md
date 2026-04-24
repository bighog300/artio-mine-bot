# Smart Mode Bug Triage and Fix Plan

## Severity policy
- **P0 (blocking):** prevents core path (URL -> record output) for any tester.
- **P1 (critical):** core path works but with severe reliability/data quality issue.
- **P2 (major):** non-blocking but meaningful usability/quality friction.
- **P3 (minor):** cosmetic, low-frequency edge case, or enhancement.

## Launch bug handling

### P0 handling
- Immediate hotfix required before continuing beta cohort.
- Assign owner and verifier within 15 minutes.
- Release patch and retest failed script step with impacted testers.
- No open P0 allowed at launch.

### P1 handling
- Must be fixed before launch cutoff.
- Validate with regression test and targeted beta rerun.
- No more than 0 unresolved P1 at launch.

### P2/P3 handling
- Document with repro and impact notes.
- Add to post-launch backlog with priority tags.
- Confirm workaround in docs if user-visible.

## Post-launch backlog seed (P2/P3)
| ID | Severity | Area | Issue | Workaround | Target Sprint |
|---|---|---|---|---|---|
| SM-P2-001 | P2 | UX | Confidence tooltip unclear for mixed-source records | Use provenance panel for source context | Sprint +1 |
| SM-P2-002 | P2 | API | Export-ready filter can lag one refresh cycle | Manual refresh in records page | Sprint +1 |
| SM-P3-001 | P3 | UI | Minor alignment issue in image card metadata | None required | Sprint +2 |
| SM-P3-002 | P3 | Docs | Need more examples for venue-only sources | FAQ entry + tutorial update | Sprint +2 |
