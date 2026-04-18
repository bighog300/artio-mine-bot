# CODEX: Execute Complete Phase 4 - Accessibility (WCAG 2.1 AA)

## MASTER EXECUTION PROMPT

Complete guide to making Artio Mine Bot WCAG 2.1 AA compliant.

---

## 📦 PHASE 4 STRUCTURE

### Week 1: Foundation (4-6 hours)
**File:** CODEX_EXECUTE_PHASE4_WEEK1.md

**Deliverables:**
- Accessibility audit complete
- ESLint accessibility rules
- Skip navigation
- Focus management
- Keyboard navigation foundation
- ARIA labels baseline

---

### Week 2-3: Pages & Components (8-12 hours)
**File:** CODEX_EXECUTE_PHASE4_WEEK2_3.md

**Deliverables:**
- All 23 pages accessible
- Forms fully labeled
- Tables semantic
- Images with alt text
- Interactive components keyboard-accessible

---

## 🎯 WCAG 2.1 AA REQUIREMENTS

### Perceivable
✅ Text alternatives (alt text)  
✅ Adaptable (semantic HTML)  
✅ Distinguishable (contrast, text size)

### Operable
✅ Keyboard accessible  
✅ Navigable (skip links, focus)  
✅ No seizures (no flashing)

### Understandable
✅ Readable (clear labels)  
✅ Predictable (consistent)  
✅ Input assistance (errors)

### Robust
✅ Compatible (valid HTML, ARIA)

---

## 🚀 QUICK START

### For Codex

```
Codex,

Execute Phase 4: Accessibility Implementation

Read and execute in order:
1. CODEX_EXECUTE_PHASE4_WEEK1.md (Foundation)
2. CODEX_EXECUTE_PHASE4_WEEK2_3.md (Pages & Components)

Goal: WCAG 2.1 AA compliance
Timeline: 12-18 hours
Testing: Keyboard, screen reader, automated

Make the app accessible to all users.
Execute now! ♿
```

---

## 📋 WHAT YOU'LL GET

### Week 1 Foundation
```
✅ Accessibility linting configured
✅ Skip to main content link
✅ Focus visible throughout
✅ Keyboard navigation working
✅ Modal focus traps
✅ ARIA labels foundation
```

### Week 2-3 Implementation
```
✅ All 23 pages accessible
✅ Unique page titles
✅ Proper heading hierarchy
✅ Forms fully accessible
✅ Tables semantic
✅ Images with alt text
✅ Interactive components keyboard-accessible
✅ Screen reader compatible
```

---

## 📊 EXPECTED RESULTS

### Before Phase 4
```
Accessibility: ⚠️ Basic
- Some keyboard navigation
- Missing alt text
- No screen reader support
- Poor focus management

Grade: C (Partial accessibility)
```

### After Week 1
```
Accessibility: ⚡ Foundation
- Skip navigation ✅
- Focus visible ✅
- Keyboard foundation ✅
- Audit complete ✅

Grade: B (Good foundation)
```

### After Week 2-3
```
Accessibility: ✅ WCAG 2.1 AA
- All pages accessible ✅
- Forms labeled ✅
- Screen reader compatible ✅
- Keyboard navigation complete ✅

Grade: A (Fully accessible)
```

---

## 🧪 TESTING STRATEGY

### Automated
```bash
# ESLint accessibility rules
npm run lint

# Axe DevTools in browser
# Lighthouse accessibility audit
```

### Manual - Keyboard
```
✅ Tab through all pages
✅ Activate all buttons (Enter/Space)
✅ Navigate modals (Escape to close)
✅ No keyboard traps
✅ Logical tab order
```

### Manual - Screen Reader
```
✅ NVDA (Windows)
✅ JAWS (Windows)
✅ VoiceOver (macOS/iOS)
✅ All content announced
✅ Forms have labels
```

### Manual - Visual
```
✅ 200% zoom readable
✅ High contrast mode
✅ Color blind simulation
✅ Sufficient contrast (4.5:1)
```

---

## ✅ SUCCESS CRITERIA

Phase 4 complete when:

### Compliance
- [ ] WCAG 2.1 AA compliant
- [ ] ESLint accessibility rules pass
- [ ] Lighthouse accessibility score 90+
- [ ] No critical issues

### Functionality
- [ ] Full keyboard navigation
- [ ] Screen reader compatible
- [ ] Proper focus management
- [ ] Semantic HTML throughout

### Testing
- [ ] Automated tests pass
- [ ] Manual keyboard test complete
- [ ] Screen reader test complete
- [ ] Zoom test complete

---

## 💡 KEY CONCEPTS

### Semantic HTML
```html
<!-- Good -->
<button>Click me</button>
<nav><ul><li><a href="/">Home</a></li></ul></nav>

<!-- Bad -->
<div onClick={...}>Click me</div>
<div class="nav">...</div>
```

### ARIA When Needed
```html
<!-- Use ARIA when HTML semantics insufficient -->
<button aria-label="Close dialog">×</button>
<div role="status" aria-live="polite">Loading...</div>
```

### Focus Management
```typescript
// Trap focus in modal
// Return focus after close
// Visible focus indicators
```

### Keyboard Navigation
```
Tab - Move forward
Shift+Tab - Move back
Enter/Space - Activate
Escape - Close
Arrow keys - Navigate
```

---

## 📈 IMPACT

### Who Benefits

**Users with:**
- Visual impairments (screen readers)
- Motor disabilities (keyboard only)
- Cognitive disabilities (clear structure)
- Situational limitations (no mouse)

**Estimated:** 15-20% of users worldwide

---

## 🎯 TIMELINE

### Week 1: Foundation (4-6 hours)
- Day 1: Audit & ESLint setup (2 hours)
- Day 2: Skip nav, focus, keyboard (2-3 hours)
- Day 3: Testing (1 hour)

### Week 2-3: Implementation (8-12 hours)
- Days 4-5: Page accessibility (4-6 hours)
- Days 6-7: Component accessibility (4-6 hours)
- Day 8: Testing & fixes (2 hours)

**Total:** 12-18 hours

---

## 🏆 CERTIFICATION

After completion, you can claim:
- ✅ WCAG 2.1 AA Compliant
- ✅ Section 508 Compliant
- ✅ ADA Compliant

Add accessibility statement to your site!

---

## 📝 ACCESSIBILITY STATEMENT

```markdown
# Accessibility Statement

Artio Mine Bot is committed to ensuring digital accessibility 
for people with disabilities. We continually improve the user 
experience for everyone and apply the relevant accessibility 
standards.

## Conformance Status

Artio Mine Bot is fully conformant with WCAG 2.1 Level AA. 
Fully conformant means that the content fully conforms to the 
accessibility standard without any exceptions.

## Feedback

We welcome your feedback on the accessibility of Artio Mine Bot. 
Please contact us if you encounter accessibility barriers.

## Compatibility

Artio Mine Bot is designed to be compatible with:
- Screen readers (NVDA, JAWS, VoiceOver)
- Keyboard navigation
- High contrast mode
- 200% zoom

Last updated: [Date]
```

---

## 🚀 READY TO EXECUTE

Give Codex this prompt:

```
Codex,

Execute Phase 4: WCAG 2.1 AA Accessibility

Execute in order:
1. CODEX_EXECUTE_PHASE4_WEEK1.md
2. CODEX_EXECUTE_PHASE4_WEEK2_3.md

Make all 23 pages accessible.
Test with keyboard and screen readers.
Target: WCAG 2.1 AA compliance.

Execute now! ♿✨
```

---

**Make your app accessible to everyone!** 🎉
