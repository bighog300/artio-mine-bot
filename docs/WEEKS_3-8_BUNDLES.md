# WEEKS 3-8 IMPLEMENTATION BUNDLES
## Frontend, Optimization, Testing & Launch

---

# WEEK 3: FRONTEND - SMART MODE UI

**Branch:** `feature/smart-mode`  
**Duration:** 5 days  
**Prerequisites:** Week 2 complete (API endpoints working)

## DELIVERABLES

- [ ] Smart Mining page with URL input
- [ ] Template selector UI
- [ ] Progress tracking page with real-time updates
- [ ] Results display
- [ ] Error handling and retry
- [ ] Routing and navigation

## FILES TO CREATE

```
frontend/src/
├── pages/
│   ├── SmartMining.tsx           # Main entry page
│   └── SmartMiningProgress.tsx   # Progress tracking
├── components/
│   └── smart-mode/
│       ├── TemplateCard.tsx      # Template selection
│       ├── StageIndicator.tsx    # Progress stage
│       └── ResultsSummary.tsx    # Results display
└── lib/
    └── api.ts                    # Add smart mine API calls

frontend/src/App.tsx              # Add routes
```

## CODEX PROMPT

```
Implement the Smart Mode frontend for Artio Mine Bot.

Create:
1. SmartMining page (/smart-mine)
   - URL input field with validation
   - Template selector cards (fetch from API)
   - "Start Smart Mining" button
   - Clean, simple interface

2. SmartMiningProgress page (/smart-mine/:sourceId/progress)
   - Real-time progress tracking (poll every 2 seconds)
   - Stage indicators (analyzing → generating → testing → mining)
   - Progress stats (pages, records)
   - Results summary on completion
   - Link to view records

3. API Integration (lib/api.ts)
   - POST /api/smart-mine/ 
   - GET /api/smart-mine/:id/status
   - GET /api/smart-mine/templates

4. Routing (App.tsx)
   - Add routes for new pages
   - Add navigation link

Use React + TypeScript + TanStack Query
Follow existing code patterns
Use shadcn/ui components
Make mobile-responsive

Success criteria:
- User can paste URL and click Start
- Progress updates every 2 seconds
- Shows clear status at each stage
- Displays results when complete
- Error handling with retry option
```

---

# WEEK 4: OPTIMIZATION & POLISH

**Branch:** `feature/smart-mode`  
**Duration:** 5 days  
**Prerequisites:** Week 3 complete (Frontend working)

## DELIVERABLES

- [ ] Prompt optimization (30% token reduction)
- [ ] Enhanced caching
- [ ] Cost tracking dashboard
- [ ] Error message improvements
- [ ] Performance tuning

## FILES TO CREATE/MODIFY

```
app/ai/
├── config_generator.py    # Optimize prompts
├── cache.py              # Enhanced caching
└── metrics.py            # Cost tracking

frontend/src/pages/
└── SmartMiningMetrics.tsx # Admin metrics dashboard
```

## CODEX PROMPT

```
Optimize Smart Mode for cost and performance:

1. Prompt Optimization
   - Reduce system prompts by 30% (keep essential rules)
   - Reduce HTML preview size (5000 → 3000 chars)
   - Smarter HTML truncation (keep important parts)
   - Test quality doesn't degrade

2. Enhanced Caching
   - Add cache statistics tracking
   - Implement cache warming for popular sites
   - Add cache invalidation on site changes
   - Monitor hit/miss ratios

3. Cost Tracking
   - Track tokens and cost per operation
   - Create metrics dashboard (admin only)
   - Alert if cost > $0.15 per URL
   - Generate daily cost reports

4. Error Messages
   - Make user-facing errors helpful
   - No technical jargon in UI messages
   - Suggest actions (retry, use guided mode)
   - Log technical details separately

Target metrics:
- 30% token reduction
- Cache hit rate > 60%
- Cost < $0.10 per URL average
- All errors have helpful messages
```

---

# WEEK 5-6: GUIDED MODE (OPTIONAL)

**Branch:** `feature/smart-mode`  
**Duration:** 10 days  
**Prerequisites:** Week 4 complete

## DELIVERABLES

- [ ] Visual selector builder (click-to-select)
- [ ] Step-by-step wizard
- [ ] Field configuration UI
- [ ] Preview panel
- [ ] Integration with backend

## FILES TO CREATE

```
frontend/src/
├── pages/
│   └── GuidedMapping.tsx
└── components/
    └── guided-mode/
        ├── Wizard.tsx
        ├── SiteTypeSelector.tsx
        ├── EntityTypePicker.tsx
        ├── VisualSelectorBuilder.tsx
        └── ConfigPreview.tsx
```

## CODEX PROMPT

```
Implement Guided Mode - visual configuration wizard:

1. Multi-Step Wizard
   Step 1: Select site type (art_gallery, event_calendar, etc.)
   Step 2: Choose entity types (artists, events, venues)
   Step 3: Pick fields to extract (checkboxes)
   Step 4: Configure selectors (visual builder)
   Step 5: Preview and confirm

2. Visual Selector Builder
   - Embed sample page in iframe
   - Click element to select
   - Auto-generate CSS selector
   - Test selector on 5 samples
   - Show preview of extracted values
   - Allow manual editing

3. Field Configuration
   - Common fields pre-populated
   - Add custom fields
   - Mark required vs optional
   - Fallback selector suggestions

4. Preview Panel
   - Show what would be extracted
   - Highlight matched elements
   - Warning for low confidence
   - Edit and re-test

Make it accessible for non-technical users.
Save generated config when complete.
```

---

# WEEK 7: BETA TESTING & POLISH

**Branch:** `feature/smart-mode`  
**Duration:** 5 days  
**Prerequisites:** Weeks 1-6 complete

## DELIVERABLES

- [ ] Beta testing with 10 users
- [ ] Bug fixes from testing
- [ ] Documentation (user guide, API docs)
- [ ] Video tutorial
- [ ] Final QA

## CODEX PROMPT

```
Prepare Smart Mode for launch:

1. Beta Testing Setup
   - Create test accounts for 10 beta testers
   - Prepare test script with success criteria
   - Set up feedback collection
   - Monitor usage analytics

2. Bug Fixes
   - Fix all P0 (blocking) issues
   - Fix critical P1 issues
   - Document P2/P3 for post-launch

3. Documentation
   - User guide: "How to use Smart Mode"
   - API documentation
   - Troubleshooting guide
   - FAQ based on beta feedback

4. Tutorial Video
   - 2-minute quickstart
   - Screen recording with voiceover
   - Show: paste URL → get records

5. Final QA
   - Test all user flows
   - Test error scenarios
   - Performance testing
   - Security review

Success criteria:
- All beta testers complete successfully
- User satisfaction > 4/5
- Time to first record < 5 min
- Success rate > 85%
```

---

# WEEK 8: LAUNCH & MONITORING

**Branch:** `feature/smart-mode`  
**Duration:** 5 days  
**Prerequisites:** Week 7 complete (Beta successful)

## DELIVERABLES

- [ ] Production deployment
- [ ] Gradual rollout (10% → 50% → 100%)
- [ ] Monitoring dashboard
- [ ] User onboarding flow
- [ ] Launch announcement

## CODEX PROMPT

```
Launch Smart Mode to production:

1. Pre-Launch Checklist
   - All tests passing
   - OpenAI API key configured
   - Rate limits set
   - Error monitoring enabled
   - Backups scheduled
   - Rollback plan ready

2. Gradual Rollout
   Day 1: 10% of users (feature flag)
   Day 2: Monitor, fix issues
   Day 3: 50% of users
   Day 4: Monitor, iterate
   Day 5: 100% of users

3. Monitoring Dashboard
   - Success rate
   - Avg time to first record
   - Cost per URL
   - Error rate
   - Template hit rate
   - User satisfaction

4. User Onboarding
   - First-time user tutorial
   - Highlight Smart Mode in nav
   - Email to existing users
   - Help tooltips

5. Launch Announcement
   - Blog post
   - Email campaign
   - Social media
   - Product Hunt (optional)

Monitor closely for 48 hours post-launch.
Quick response to any issues.
```

---

# IMPLEMENTATION TRACKING

## Week-by-Week Summary

**Week 1:** ✅ Backend foundation (AI services)  
**Week 2:** ✅ API endpoints & templates  
**Week 3:** Frontend UI  
**Week 4:** Optimization  
**Week 5-6:** Guided Mode (optional)  
**Week 7:** Testing & polish  
**Week 8:** Launch  

## After Each Week

Please provide:

1. **What was completed**
   - List of implemented features
   - Any deviations from plan

2. **Metrics**
   - Performance measurements
   - Cost per URL (actual)
   - Success rates

3. **Issues encountered**
   - Blockers
   - Technical debt
   - Known limitations

4. **Recommendations**
   - What to adjust for next week
   - Priority changes
   - Risk mitigation

---

# POST-LAUNCH TRACKING TEMPLATE

After Week 8 launch, track these metrics weekly:

```markdown
## Week [X] Post-Launch Metrics

### Usage
- Smart mines started: [number]
- Success rate: [percentage]
- Template hit rate: [percentage]
- Avg time to first record: [minutes]

### Quality
- User satisfaction: [1-5 rating]
- Support tickets: [number]
- Bug reports: [number]

### Cost
- Total API costs: $[amount]
- Avg cost per URL: $[amount]
- Total URLs mined: [number]

### Action Items
- [ ] [Item 1]
- [ ] [Item 2]

### Wins
- [Notable success story]

### Issues
- [Problem and resolution]
```

---

# FINAL INTEGRATION CHECKLIST

Before marking the project complete:

## Technical
- [ ] All tests passing (>90% coverage)
- [ ] No critical bugs
- [ ] Performance targets met
- [ ] Security review passed
- [ ] API documentation complete
- [ ] Error monitoring active

## Product
- [ ] User guide published
- [ ] Tutorial video recorded
- [ ] FAQ complete
- [ ] Support team trained
- [ ] Analytics tracking

## Deployment
- [ ] Production deployed
- [ ] 100% rollout complete
- [ ] Monitoring dashboard live
- [ ] Rollback plan tested
- [ ] On-call rotation set

## Success Metrics
- [ ] Success rate > 85%
- [ ] Time to first record < 5 min
- [ ] User satisfaction > 4/5
- [ ] Cost per URL < $0.10
- [ ] Template hit rate > 40%

---

# REPOSITORY UPLOAD PROCEDURE

After each week's Codex run:

1. **Upload repo ZIP to Claude**
2. **Provide summary:**
   ```
   Week [N] completed.
   
   Implemented:
   - [Feature 1]
   - [Feature 2]
   
   Metrics:
   - Success rate: [X]%
   - Cost per URL: $[X]
   
   Issues:
   - [Issue 1]
   - [Issue 2]
   
   Next: Week [N+1] ready
   ```

3. **Claude will review and create:**
   - Issues list for final pass
   - Recommendations for next week
   - Updated risk assessment

4. **Repeat for each week**

---

# FINAL PASS CHECKLIST

After Week 8, final repo review will check:

## Code Quality
- [ ] No TODOs or FIXMEs
- [ ] All console.logs removed
- [ ] Error handling comprehensive
- [ ] Types properly defined
- [ ] No dead code

## Testing
- [ ] All tests passing
- [ ] Edge cases covered
- [ ] Integration tests complete
- [ ] Performance tests run

## Documentation
- [ ] README updated
- [ ] API docs complete
- [ ] Code comments clear
- [ ] Architecture documented

## Deployment
- [ ] Environment variables documented
- [ ] Migration scripts ready
- [ ] Monitoring configured
- [ ] Alerts set up

## Performance
- [ ] No memory leaks
- [ ] Response times acceptable
- [ ] Rate limiting working
- [ ] Caching effective

## Security
- [ ] API keys not hardcoded
- [ ] Input validation everywhere
- [ ] SQL injection prevented
- [ ] XSS protection
- [ ] CORS configured properly

---

END OF IMPLEMENTATION BUNDLES
