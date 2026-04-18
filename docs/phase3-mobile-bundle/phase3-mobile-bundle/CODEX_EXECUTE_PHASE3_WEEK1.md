# CODEX: Execute Phase 3 - Mobile Responsive Design

## CONTEXT

You are executing **Phase 3** of the Nice-to-Have Implementation Plan found in `/docs/NICE_TO_HAVE_IMPLEMENTATION_PLAN.md`.

**Goal:** Make all 22 pages fully responsive and functional on mobile devices (phones and tablets).

**Timeline:** 3-4 weeks (execute in stages)

**Current State:**
- Desktop-optimized layout
- Component library complete (Phase 2 ✅)
- Dark mode complete (Phase 5 ✅)
- No mobile optimization
- Fixed layouts that break on small screens

**Target State:**
- All 22 pages work on mobile (320px - 768px)
- Touch-friendly interactions
- Responsive layouts (mobile-first approach)
- Tablet optimization (768px - 1024px)
- Mobile navigation (hamburger menu)
- Touch gestures where appropriate
- Performance optimized for mobile

---

## PHASE 3 STRUCTURE

This phase is broken into **4 sub-phases**:

1. **Week 1:** Mobile Foundation (breakpoints, navigation, utilities)
2. **Week 2:** Core Pages (Dashboard, Sources, Records - most used)
3. **Week 3:** Operational Pages (Jobs, Logs, Workers, etc.)
4. **Week 4:** Polish & Testing (all pages, performance, gestures)

Execute **Week 1 now**, then we'll proceed to core pages.

---

## MOBILE DESIGN PRINCIPLES

### Breakpoint Strategy

```typescript
// Use Tailwind's default breakpoints
sm:  640px  // Small tablets (portrait)
md:  768px  // Tablets (landscape) / Small laptops
lg:  1024px // Laptops
xl:  1280px // Desktops
2xl: 1536px // Large desktops

// Mobile-first approach
// Base styles = mobile (< 640px)
// Add complexity as screen grows
```

### Touch-Friendly Design

```typescript
// Minimum touch target: 44x44px (iOS) / 48x48px (Android)
// Use larger buttons on mobile
// Increase padding around interactive elements
// Avoid hover-dependent interactions
// Add touch feedback (active states)
```

### Mobile Navigation Patterns

```typescript
// Desktop: Sidebar navigation
// Mobile: Hamburger menu + bottom navigation (optional)
// Tablet: Collapsible sidebar
```

---

## WEEK 1: MOBILE FOUNDATION

### TASK 1: UPDATE BREAKPOINT TOKENS

**File:** `frontend/src/lib/tokens.ts`

Add mobile-specific tokens:

```typescript
// Add to existing tokens
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

export const spacing = {
  // ... existing spacing ...
  
  // Mobile-specific spacing
  mobile: {
    padding: '1rem',      // 16px
    margin: '0.75rem',    // 12px
    gap: '0.75rem',       // 12px
  },
  
  // Touch targets
  touch: {
    minHeight: '44px',    // iOS minimum
    minWidth: '44px',
    preferred: '48px',    // Android minimum
  },
};
```

---

### TASK 2: CREATE MOBILE NAVIGATION

**File:** `frontend/src/components/shared/MobileNav.tsx`

```typescript
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/cn';

interface NavItem {
  path: string;
  label: string;
  icon?: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard' },
  { path: '/sources', label: 'Sources' },
  { path: '/records', label: 'Records' },
  { path: '/jobs', label: 'Jobs' },
  { path: '/workers', label: 'Workers' },
  { path: '/logs', label: 'Logs' },
  { path: '/settings', label: 'Settings' },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  
  return (
    <>
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-background border-b border-border z-50">
        <div className="flex items-center justify-between h-full px-4">
          <h1 className="text-lg font-semibold text-foreground">
            Artio Mine Bot
          </h1>
          
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-2 hover:bg-muted rounded-lg"
            aria-label="Toggle menu"
          >
            {isOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>
        </div>
      </header>
      
      {/* Mobile Menu Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40 top-14"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      {/* Mobile Menu */}
      <nav
        className={cn(
          'lg:hidden fixed top-14 right-0 w-64 h-[calc(100vh-3.5rem)] bg-background border-l border-border z-40',
          'transform transition-transform duration-200',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <div className="flex flex-col p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setIsOpen(false)}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                'min-h-[48px]', // Touch-friendly height
                location.pathname === item.path
                  ? 'bg-primary text-primary-foreground'
                  : 'text-foreground hover:bg-muted'
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  );
}
```

---

### TASK 3: UPDATE LAYOUT FOR MOBILE

**File:** `frontend/src/components/shared/Layout.tsx`

```typescript
import { MobileNav } from './MobileNav';
import { ThemeToggle } from './ThemeToggle';

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      {/* Desktop Sidebar - hidden on mobile */}
      <aside className="hidden lg:flex w-64 border-r border-border bg-background flex-col">
        {/* Existing sidebar content */}
      </aside>
      
      {/* Mobile Navigation */}
      <MobileNav />
      
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Desktop Header - hidden on mobile */}
        <header className="hidden lg:flex h-16 border-b border-border bg-background items-center justify-between px-6">
          <h1 className="text-xl font-semibold text-foreground">
            Artio Mine Bot
          </h1>
          <ThemeToggle />
        </header>
        
        {/* Page content - with mobile padding */}
        <main className={cn(
          'flex-1 overflow-auto bg-background',
          'pt-14 lg:pt-0', // Add top padding on mobile for fixed header
          'px-4 lg:px-6',   // Smaller horizontal padding on mobile
          'py-4 lg:py-6'    // Smaller vertical padding on mobile
        )}>
          {children}
        </main>
      </div>
    </div>
  );
}
```

---

### TASK 4: CREATE MOBILE-FRIENDLY UTILITIES

**File:** `frontend/src/lib/mobile-utils.ts`

```typescript
import { useEffect, useState } from 'react';

/**
 * Hook to detect if viewport is mobile
 */
export function useIsMobile(breakpoint: number = 768) {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < breakpoint);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, [breakpoint]);
  
  return isMobile;
}

/**
 * Hook to detect touch device
 */
export function useIsTouchDevice() {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

/**
 * Hook for viewport dimensions
 */
export function useViewport() {
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  
  useEffect(() => {
    const handleResize = () => {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  return viewport;
}
```

---

### TASK 5: UPDATE BUTTON COMPONENT FOR MOBILE

**File:** `frontend/src/components/ui/Button.tsx`

Add mobile-friendly sizing:

```typescript
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean; // New: full width on mobile
  loading?: boolean;
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    variant = 'primary', 
    size = 'md', 
    fullWidth = false,
    loading = false,
    icon,
    disabled,
    className,
    children,
    ...props 
  }, ref) => {
    const baseStyles = cn(
      'inline-flex items-center justify-center gap-2 font-medium rounded-lg',
      'transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'touch-manipulation', // Improves touch response
      fullWidth && 'w-full'
    );
    
    const variantStyles = {
      // ... existing variants ...
    };
    
    const sizeStyles = {
      sm: 'px-3 py-1.5 text-sm min-h-[36px]',
      md: 'px-4 py-2 text-base min-h-[44px]', // Touch-friendly
      lg: 'px-6 py-3 text-lg min-h-[48px]',   // Touch-friendly
    };
    
    return (
      <button
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )}
        {icon && !loading && icon}
        {children}
      </button>
    );
  }
);
```

---

### TASK 6: UPDATE TABLE COMPONENT FOR MOBILE

**File:** `frontend/src/components/ui/Table.tsx`

Add mobile-responsive wrapper:

```typescript
import { cn } from '@/lib/cn';

export function Table({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto -mx-4 px-4 lg:mx-0 lg:px-0">
      <table
        className={cn('w-full text-sm min-w-[640px]', className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead
      className={cn('bg-muted border-b', className)}
      {...props}
    />
  );
}

export function TableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody
      className={cn('divide-y divide-border', className)}
      {...props}
    />
  );
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        'hover:bg-muted/40 transition-colors',
        'active:bg-muted/60', // Touch feedback
        className
      )}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider',
        'lg:px-4', // More padding on desktop
        className
      )}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        'px-3 py-3 text-foreground text-sm',
        'lg:px-4',
        className
      )}
      {...props}
    />
  );
}
```

---

### TASK 7: CREATE MOBILE CARD COMPONENT

**File:** `frontend/src/components/ui/MobileCard.tsx`

Alternative to tables on mobile:

```typescript
import { cn } from '@/lib/cn';

interface MobileCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function MobileCard({ children, className, onClick }: MobileCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-card border border-border rounded-lg p-4',
        'space-y-2',
        'active:bg-muted/40', // Touch feedback
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
}

export function MobileCardRow({ 
  label, 
  value, 
  className 
}: { 
  label: string; 
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex justify-between items-start', className)}>
      <span className="text-sm text-muted-foreground font-medium">
        {label}
      </span>
      <span className="text-sm text-foreground text-right ml-4">
        {value}
      </span>
    </div>
  );
}
```

---

### TASK 8: ADD RESPONSIVE GRID UTILITIES

**File:** `frontend/src/components/ui/ResponsiveGrid.tsx`

```typescript
import { cn } from '@/lib/cn';

interface ResponsiveGridProps {
  children: React.ReactNode;
  className?: string;
  cols?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
  };
}

export function ResponsiveGrid({ 
  children, 
  className,
  cols = { mobile: 1, tablet: 2, desktop: 3 }
}: ResponsiveGridProps) {
  return (
    <div
      className={cn(
        'grid gap-4',
        `grid-cols-${cols.mobile}`,
        `md:grid-cols-${cols.tablet}`,
        `lg:grid-cols-${cols.desktop}`,
        className
      )}
    >
      {children}
    </div>
  );
}
```

---

### TASK 9: UPDATE MODAL FOR MOBILE

**File:** `frontend/src/components/ui/Modal.tsx`

Make modals full-screen on mobile:

```typescript
export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [open]);
  
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (open) {
      window.addEventListener('keydown', handleEscape);
      return () => window.removeEventListener('keydown', handleEscape);
    }
  }, [open, onClose]);
  
  if (!open) return null;
  
  const sizeStyles = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-end lg:items-center justify-center p-0 lg:p-4">
        <div
          className={cn(
            'bg-background shadow-xl w-full overflow-hidden',
            'rounded-t-2xl lg:rounded-lg', // Rounded top on mobile, all sides on desktop
            'max-h-[90vh] lg:max-h-[85vh]', // Full height on mobile
            'lg:w-auto', // Auto width on desktop
            sizeStyles[size]
          )}
          role="dialog"
          aria-modal="true"
        >
          {/* Header */}
          {title && (
            <div className="flex items-center justify-between px-4 py-4 lg:px-6 border-b sticky top-0 bg-background z-10">
              <h2 className="text-lg font-semibold text-foreground">{title}</h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-muted rounded-lg transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label="Close"
              >
                <X className="h-5 w-5 text-muted-foreground" />
              </button>
            </div>
          )}
          
          {/* Content */}
          <div className="overflow-auto">
            {children}
          </div>
        </div>
      </div>
    </>
  );
}

export function ModalContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-4 py-4 lg:px-6', className)} {...props}>
      {children}
    </div>
  );
}

export function ModalFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div 
      className={cn(
        'px-4 py-4 lg:px-6 border-t bg-muted/40',
        'flex flex-col-reverse lg:flex-row lg:justify-end gap-3',
        'sticky bottom-0', // Sticky footer
        className
      )} 
      {...props}
    >
      {children}
    </div>
  );
}
```

---

### TASK 10: CREATE MOBILE TEST PAGE

**File:** `frontend/src/pages/MobileTest.tsx`

```typescript
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { MobileCard, MobileCardRow } from '@/components/ui/MobileCard';
import { useIsMobile, useViewport } from '@/lib/mobile-utils';

export function MobileTest() {
  const isMobile = useIsMobile();
  const viewport = useViewport();
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground mb-2">
          Mobile Test Page
        </h1>
        <p className="text-sm text-muted-foreground">
          Device: {isMobile ? 'Mobile' : 'Desktop'} | 
          Viewport: {viewport.width}x{viewport.height}
        </p>
      </div>
      
      {/* Buttons */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Buttons</h2>
        <div className="space-y-2">
          <Button fullWidth variant="primary">Full Width Primary</Button>
          <Button fullWidth variant="secondary">Full Width Secondary</Button>
          <div className="flex gap-2">
            <Button className="flex-1">Half</Button>
            <Button className="flex-1">Half</Button>
          </div>
        </div>
      </section>
      
      {/* Form Elements */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Form Elements</h2>
        <Input label="Email" type="email" placeholder="you@example.com" />
        <Select
          label="Country"
          options={[
            { value: 'us', label: 'United States' },
            { value: 'uk', label: 'United Kingdom' },
          ]}
        />
      </section>
      
      {/* Cards */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Mobile Cards</h2>
        <MobileCard>
          <MobileCardRow label="Name" value="John Doe" />
          <MobileCardRow label="Email" value="john@example.com" />
          <MobileCardRow label="Status" value={<span className="text-green-600">Active</span>} />
        </MobileCard>
      </section>
    </div>
  );
}
```

Add route:
```typescript
<Route path="/mobile-test" element={<MobileTest />} />
```

---

## VERIFICATION CHECKLIST (Week 1)

After executing Week 1 tasks:

- [ ] Mobile navigation created
- [ ] Layout responsive on mobile
- [ ] Breakpoint utilities added
- [ ] Mobile hooks created
- [ ] Button component mobile-friendly
- [ ] Table component responsive
- [ ] MobileCard component created
- [ ] Modal full-screen on mobile
- [ ] Test page renders correctly
- [ ] No horizontal scroll on mobile
- [ ] Touch targets minimum 44px
- [ ] Build successful
- [ ] Tests passing

---

## TESTING MOBILE

### Browser DevTools

```bash
1. Open Chrome DevTools (F12)
2. Click device toolbar icon (Ctrl+Shift+M)
3. Select device:
   - iPhone 12 Pro (390x844)
   - iPad Air (820x1180)
   - Pixel 5 (393x851)
4. Test:
   - Navigation opens/closes
   - Buttons are touch-friendly
   - Forms are usable
   - Tables scroll horizontally
   - Modals are full-screen
```

### Responsive Breakpoints

```bash
Test at these widths:
- 320px  (Smallest phones)
- 375px  (iPhone SE)
- 390px  (iPhone 12/13/14)
- 414px  (iPhone Plus)
- 640px  (sm breakpoint)
- 768px  (md breakpoint - tablet)
- 1024px (lg breakpoint - desktop)
```

---

## COMMIT MESSAGE (Week 1)

```
feat: add mobile responsive foundation

Mobile Infrastructure:
- Add mobile breakpoint tokens
- Create mobile navigation with hamburger menu
- Add mobile utility hooks (useIsMobile, useViewport)
- Update Layout for mobile/desktop switching

Component Updates:
- Button: Touch-friendly sizing (44px min-height)
- Button: fullWidth prop for mobile
- Table: Horizontal scroll on mobile
- Modal: Full-screen bottom sheet on mobile
- Modal: Sticky header/footer

New Components:
- MobileNav: Slide-out navigation menu
- MobileCard: Alternative to tables on mobile
- ResponsiveGrid: Grid that adapts to screen size

Testing:
- Mobile test page created
- Touch targets verified (44px+)
- No horizontal scroll on mobile
- All components responsive

Closes: Phase 3, Week 1 - Mobile Foundation
```

---

## EXECUTION STEPS (Week 1)

1. **Add mobile tokens:**
   ```bash
   # Edit frontend/src/lib/tokens.ts
   # Add breakpoints and mobile spacing
   ```

2. **Create mobile navigation:**
   ```bash
   # Create frontend/src/components/shared/MobileNav.tsx
   # Update Layout.tsx for mobile
   ```

3. **Add mobile utilities:**
   ```bash
   # Create frontend/src/lib/mobile-utils.ts
   ```

4. **Update components:**
   ```bash
   # Update Button.tsx, Table.tsx, Modal.tsx
   # Create MobileCard.tsx, ResponsiveGrid.tsx
   ```

5. **Create test page:**
   ```bash
   # Create MobileTest.tsx
   # Add route
   ```

6. **Test in DevTools:**
   ```bash
   npm run dev
   # Test at 320px, 375px, 768px
   ```

7. **Verify & commit:**
   ```bash
   npm run build
   npm test
   git add .
   git commit -m "feat: add mobile responsive foundation"
   ```

---

## NEXT STEPS

After Week 1 completes:
- **Week 2:** Core Pages (Dashboard, Sources, Records)
- **Week 3:** Operational Pages (Jobs, Logs, Workers, etc.)
- **Week 4:** Polish & Testing

---

Ready to make the app mobile-friendly! 📱
