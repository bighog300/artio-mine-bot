# CODEX: Execute Phase 4, Week 1 - Accessibility Foundation

## CONTEXT

You are executing **Phase 4, Week 1** of the Accessibility implementation for Artio Mine Bot.

**Goal:** Establish accessibility foundation and audit current state.

**Timeline:** Week 1 (4-6 hours)

**Target:** WCAG 2.1 AA compliance

**Prerequisites:**
- ✅ All phases 1-3, 5 complete
- ✅ Component library in place
- ✅ Dark mode working
- ✅ Mobile responsive

**Target State:**
- Accessibility audit complete
- Skip navigation implemented
- Focus management system
- Keyboard navigation foundation
- ARIA labels where needed
- Color contrast verified

---

## WCAG 2.1 AA REQUIREMENTS

### Perceivable
1. **Text Alternatives** - Alt text for images
2. **Time-based Media** - Captions (if applicable)
3. **Adaptable** - Semantic HTML
4. **Distinguishable** - Color contrast, text sizing

### Operable
1. **Keyboard Accessible** - All functions via keyboard
2. **Enough Time** - No time limits (or adjustable)
3. **Seizures** - No flashing content
4. **Navigable** - Skip links, page titles, focus order

### Understandable
1. **Readable** - Language specified, clear labels
2. **Predictable** - Consistent navigation
3. **Input Assistance** - Error identification, labels

### Robust
1. **Compatible** - Valid HTML, ARIA

---

## TASK 1: ACCESSIBILITY AUDIT

### Step 1: Install Audit Tools

```bash
# Install axe-core for automated testing
npm install --save-dev @axe-core/react

# Install eslint-plugin-jsx-a11y
npm install --save-dev eslint-plugin-jsx-a11y
```

---

### Step 2: Configure ESLint for Accessibility

**File:** `frontend/.eslintrc.cjs` (or `.eslintrc.json`)

```javascript
module.exports = {
  extends: [
    // ... existing extends
    'plugin:jsx-a11y/recommended',
  ],
  plugins: [
    // ... existing plugins
    'jsx-a11y',
  ],
  rules: {
    // Accessibility rules
    'jsx-a11y/alt-text': 'error',
    'jsx-a11y/aria-props': 'error',
    'jsx-a11y/aria-proptypes': 'error',
    'jsx-a11y/aria-unsupported-elements': 'error',
    'jsx-a11y/click-events-have-key-events': 'warn',
    'jsx-a11y/heading-has-content': 'error',
    'jsx-a11y/html-has-lang': 'error',
    'jsx-a11y/img-redundant-alt': 'error',
    'jsx-a11y/interactive-supports-focus': 'warn',
    'jsx-a11y/label-has-associated-control': 'error',
    'jsx-a11y/no-autofocus': 'warn',
    'jsx-a11y/no-distracting-elements': 'error',
    'jsx-a11y/no-redundant-roles': 'error',
    'jsx-a11y/role-has-required-aria-props': 'error',
    'jsx-a11y/role-supports-aria-props': 'error',
    'jsx-a11y/scope': 'error',
    'jsx-a11y/tabindex-no-positive': 'error',
  },
};
```

---

### Step 3: Run Automated Audit

```bash
# Run ESLint
npm run lint

# Note all accessibility warnings/errors
# Create file: accessibility-audit.md
```

**Create:** `frontend/docs/accessibility-audit.md`

```markdown
# Accessibility Audit Results

## Date: [Current Date]

### Automated Issues Found

#### Critical (Must Fix)
- [ ] Missing alt text on images
- [ ] Form inputs without labels
- [ ] Missing ARIA labels
- [ ] Poor color contrast
- [ ] Invalid ARIA attributes

#### Warnings (Should Fix)
- [ ] Click events without keyboard handlers
- [ ] Interactive elements without focus
- [ ] Missing skip navigation

#### Notes
- Document all issues found
- Prioritize by severity
- Track fixes in subsequent weeks
```

---

### Step 4: Manual Keyboard Navigation Test

**Test every page with keyboard only (no mouse):**

```
Tab - Move forward
Shift+Tab - Move backward
Enter - Activate links/buttons
Space - Toggle checkboxes/buttons
Arrow keys - Navigate within components
Escape - Close modals/dropdowns
```

**Create checklist:**

```markdown
## Keyboard Navigation Test

### Dashboard
- [ ] Can Tab to all interactive elements
- [ ] Focus visible on all elements
- [ ] Can activate all buttons with Enter/Space
- [ ] Logical tab order
- [ ] No keyboard traps

### Sources
- [ ] Can navigate table with keyboard
- [ ] Can open/close create dialog
- [ ] Can submit form with keyboard
- [ ] Focus returns after modal close

### Records
- [ ] Can filter with keyboard
- [ ] Can navigate cards/table
- [ ] Can interact with all controls

[Continue for all 23 pages]
```

---

## TASK 2: SKIP NAVIGATION

**File:** `frontend/src/components/shared/Layout.tsx`

### Step 1: Add Skip Link

```typescript
export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      {/* Skip Navigation Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 bg-primary text-primary-foreground px-4 py-2 rounded-md font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring"
      >
        Skip to main content
      </a>
      
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-56 flex-col border-r border-border bg-card">
        {/* ... sidebar content ... */}
      </aside>
      
      {/* Mobile Navigation */}
      <MobileNav />
      
      {/* Main content */}
      <main 
        id="main-content" 
        className="flex-1 overflow-auto bg-background pt-14 lg:pt-0 px-4 lg:px-6 py-4 lg:py-6"
        tabIndex={-1} // Allow programmatic focus
      >
        {children}
      </main>
    </div>
  );
}
```

### Step 2: Add Screen Reader Only Utility

**File:** `frontend/src/index.css`

```css
/* Screen reader only - visible when focused */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.focus\:not-sr-only:focus {
  position: static;
  width: auto;
  height: auto;
  padding: inherit;
  margin: inherit;
  overflow: visible;
  clip: auto;
  white-space: normal;
}
```

---

## TASK 3: FOCUS MANAGEMENT

### Step 1: Focus Visible Styles

**File:** `frontend/src/index.css`

```css
/* Custom focus styles for better visibility */
@layer base {
  *:focus-visible {
    outline: 2px solid hsl(var(--ring));
    outline-offset: 2px;
  }
  
  /* Remove default outline */
  *:focus {
    outline: none;
  }
}
```

---

### Step 2: Update Button Component

**File:** `frontend/src/components/ui/Button.tsx`

Add focus-visible classes:

```typescript
export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex touch-manipulation items-center justify-center gap-2 rounded-md font-medium transition-colors',
        // Focus styles
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        // Existing styles
        variantStyles[variant],
        sizeStyles[size],
        'disabled:cursor-not-allowed disabled:opacity-60',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

### Step 3: Update Input Component

**File:** `frontend/src/components/ui/Input.tsx`

```typescript
export function Input({
  label,
  error,
  helperText,
  id,
  required,
  className,
  ...props
}: InputProps) {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;
  
  return (
    <div className="space-y-1.5">
      {label && (
        <label 
          htmlFor={inputId}
          className="block text-sm font-medium text-foreground"
        >
          {label}
          {required && <span className="text-destructive ml-1" aria-label="required">*</span>}
        </label>
      )}
      
      <input
        id={inputId}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={cn(
          error && errorId,
          helperText && helperId
        )}
        aria-required={required}
        className={cn(
          'w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground',
          'placeholder:text-muted-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-destructive focus-visible:ring-destructive',
          className
        )}
        {...props}
      />
      
      {helperText && !error && (
        <p id={helperId} className="text-sm text-muted-foreground">
          {helperText}
        </p>
      )}
      
      {error && (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

---

## TASK 4: KEYBOARD NAVIGATION

### Step 1: Add Keyboard Handler Hook

**File:** `frontend/src/hooks/useKeyboard.ts`

```typescript
import { useEffect } from 'react';

export function useKeyboard(
  key: string,
  handler: (e: KeyboardEvent) => void,
  deps: any[] = []
) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === key) {
        handler(e);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [key, handler, ...deps]);
}

export function useEscapeKey(handler: () => void) {
  useKeyboard('Escape', handler);
}

export function useEnterKey(handler: () => void) {
  useKeyboard('Enter', handler);
}
```

---

### Step 2: Update Modal for Keyboard

**File:** `frontend/src/components/ui/Modal.tsx`

```typescript
import { useEscapeKey } from '@/hooks/useKeyboard';
import { useEffect, useRef } from 'react';

export function Modal({ open, onClose, title, children }: ModalProps) {
  const previousFocus = useRef<HTMLElement | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  
  // Close on Escape
  useEscapeKey(() => {
    if (open) onClose();
  });
  
  // Focus management
  useEffect(() => {
    if (open) {
      // Save current focus
      previousFocus.current = document.activeElement as HTMLElement;
      
      // Focus modal
      setTimeout(() => {
        modalRef.current?.focus();
      }, 0);
      
      // Trap focus in modal
      const trapFocus = (e: KeyboardEvent) => {
        if (e.key === 'Tab' && modalRef.current) {
          const focusableElements = modalRef.current.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          const firstElement = focusableElements[0] as HTMLElement;
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;
          
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };
      
      window.addEventListener('keydown', trapFocus);
      
      return () => {
        window.removeEventListener('keydown', trapFocus);
        // Restore focus
        previousFocus.current?.focus();
      };
    }
  }, [open]);
  
  if (!open) return null;
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Modal */}
      <div 
        ref={modalRef}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        tabIndex={-1}
      >
        <div className="bg-background rounded-lg shadow-xl max-w-lg w-full">
          {title && (
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 id="modal-title" className="text-lg font-semibold">
                {title}
              </h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-muted rounded-lg focus-visible:outline-none focus-visible:ring-2"
                aria-label="Close dialog"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          )}
          
          <div className="px-6 py-4">
            {children}
          </div>
        </div>
      </div>
    </>
  );
}
```

---

## TASK 5: ARIA LABELS

### Step 1: Update IconButton

**File:** `frontend/src/components/ui/IconButton.tsx`

```typescript
interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  'aria-label': string; // Make required
}

export function IconButton({
  children,
  className,
  'aria-label': ariaLabel,
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center justify-center rounded-md p-2',
        'hover:bg-accent transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'min-h-[44px] min-w-[44px]', // Touch target
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

### Step 2: Update MobileNav

**File:** `frontend/src/components/shared/MobileNav.tsx`

Add ARIA attributes:

```typescript
export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-border bg-card lg:hidden">
        <div className="flex h-full items-center justify-between px-4">
          <h1 className="text-base font-semibold text-foreground">
            Artio Miner
          </h1>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2"
              aria-label={isOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={isOpen}
              aria-controls="mobile-navigation"
            >
              {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </header>
      
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 top-14 z-40 bg-black/50 lg:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
      
      {/* Navigation */}
      <nav
        id="mobile-navigation"
        className={cn(
          'fixed right-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-72 border-l border-border bg-card transition-transform duration-200 lg:hidden',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
        aria-label="Mobile navigation"
      >
        {/* Nav items */}
      </nav>
    </>
  );
}
```

---

## TASK 6: COLOR CONTRAST AUDIT

### Step 1: Check Contrast Ratios

Use tools to verify:
- **Normal text:** 4.5:1 minimum
- **Large text:** 3:1 minimum (18pt or 14pt bold)
- **UI components:** 3:1 minimum

**Online tools:**
- WebAIM Contrast Checker
- Chrome DevTools (Lighthouse)

---

### Step 2: Document Contrast Issues

Create file: `frontend/docs/contrast-issues.md`

```markdown
# Color Contrast Issues

## Current Issues

### Text on Background
- [ ] Primary text on white: [ratio]
- [ ] Muted text on white: [ratio]
- [ ] Link text: [ratio]

### Dark Mode
- [ ] Primary text on dark: [ratio]
- [ ] Muted text on dark: [ratio]

### UI Components
- [ ] Button states: [ratio]
- [ ] Input borders: [ratio]
- [ ] Disabled states: [ratio]

## Fixes Needed
[List fixes]
```

---

## TESTING CHECKLIST

After Week 1 implementation:

### Automated
- [ ] ESLint accessibility rules pass
- [ ] No critical accessibility errors
- [ ] Warnings documented

### Manual - Keyboard
- [ ] Tab through all pages
- [ ] All interactive elements reachable
- [ ] Focus visible everywhere
- [ ] No keyboard traps
- [ ] Logical tab order

### Manual - Screen Reader
- [ ] NVDA/JAWS on Windows
- [ ] VoiceOver on macOS/iOS
- [ ] Skip link announced
- [ ] All content readable
- [ ] Forms have labels

### Manual - Visual
- [ ] Focus visible (high contrast)
- [ ] Text readable at 200% zoom
- [ ] No information by color only
- [ ] Sufficient contrast

---

## COMMIT MESSAGE

```
feat: implement accessibility foundation (Phase 4 Week 1)

Accessibility Infrastructure:
- Add eslint-plugin-jsx-a11y
- Configure accessibility linting rules
- Document audit findings

Skip Navigation:
- Add skip to main content link
- Focus management on skip
- Screen reader only utility class

Focus Management:
- Custom focus-visible styles
- Focus trap in modals
- Previous focus restoration
- Keyboard handlers hook

Component Updates:
- Button: focus-visible ring
- Input: ARIA labels and descriptions
- Modal: keyboard navigation, focus trap
- IconButton: required aria-label
- MobileNav: ARIA attributes

Documentation:
- Accessibility audit results
- Contrast issues documented
- Keyboard navigation checklist

Testing:
- Manual keyboard navigation tested
- Screen reader compatibility verified
- Focus visible on all interactive elements

Standards: WCAG 2.1 AA compliance in progress
```

---

## SUCCESS CRITERIA

Week 1 complete when:

- [ ] ESLint accessibility rules configured
- [ ] Automated audit complete
- [ ] Skip navigation working
- [ ] Focus visible everywhere
- [ ] Keyboard navigation documented
- [ ] ARIA labels where needed
- [ ] Modal focus trap working
- [ ] Contrast issues documented
- [ ] Manual testing complete
- [ ] Committed to git

---

Ready to build accessibility foundation! ♿✨
