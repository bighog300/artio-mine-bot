# CODEX: Execute Phase 4, Week 2-3 - Page-Level Accessibility

## CONTEXT

Weeks 2-3 of Phase 4: Apply accessibility improvements to all pages.

**Timeline:** 8-12 hours  
**Pages:** All 23 pages  
**Goal:** WCAG 2.1 AA compliance

---

## WEEK 2: CORE & OPERATIONAL PAGES

### Task 1: Add Page Titles

Every page needs a unique `<title>`:

```typescript
// Use react-helmet or set document.title
import { useEffect } from 'react';

export function Dashboard() {
  useEffect(() => {
    document.title = 'Dashboard - Artio Mine Bot';
  }, []);
  
  return <div>...</div>;
}
```

**Pages to update (all 23):**
- Dashboard, Sources, Records, etc.

---

### Task 2: Heading Hierarchy

Ensure proper heading structure (h1 → h2 → h3):

```typescript
// Dashboard.tsx
<h1>Dashboard</h1>
<section>
  <h2>Statistics</h2>
  <div>...</div>
</section>
<section>
  <h2>Recent Activity</h2>
  <div>...</div>
</section>
```

**Fix on all pages:**
- Only one h1 per page
- No skipped levels (h1 → h3)
- Logical hierarchy

---

### Task 3: Form Accessibility

All forms need proper labels and error handling:

```typescript
// Source create form
<form onSubmit={handleSubmit} aria-label="Create new source">
  <Input
    label="Source Name"
    id="source-name"
    required
    error={errors.name}
    aria-describedby="name-helper"
  />
  
  <Input
    label="URL"
    type="url"
    required
    error={errors.url}
    helperText="Enter the full URL including https://"
  />
  
  <Button type="submit">Create Source</Button>
</form>
```

**Forms to fix:**
- Source creation
- Record creation/editing
- Settings forms
- Export configuration
- All filter forms

---

### Task 4: Table Accessibility

Tables need proper semantic markup:

```typescript
<table role="table" aria-label="Sources list">
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">URL</th>
      <th scope="col">Status</th>
      <th scope="col">Actions</th>
    </tr>
  </thead>
  <tbody>
    {sources.map(source => (
      <tr key={source.id}>
        <th scope="row">{source.name}</th>
        <td>{source.url}</td>
        <td><StatusBadge status={source.status} /></td>
        <td>
          <IconButton
            onClick={() => navigate(`/sources/${source.id}`)}
            aria-label={`View ${source.name} details`}
          >
            <Eye />
          </IconButton>
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

**Tables to fix:**
- Sources, Records, Jobs
- Workers, Queues, Pages
- Logs, Backfill

---

### Task 5: Image Alt Text

All images need descriptive alt text:

```typescript
// Record images
<img
  src={record.image_url}
  alt={record.title || 'Record thumbnail'}
  className="w-full h-auto"
/>

// Decorative images
<img
  src="/logo.svg"
  alt="" // Empty for decorative
  aria-hidden="true"
/>
```

**Images to fix:**
- Record thumbnails
- Source previews
- User avatars
- Decorative images
- Icons (use aria-label on parent)

---

### Task 6: Loading & Error States

Announce loading and errors to screen readers:

```typescript
{isLoading && (
  <div
    role="status"
    aria-live="polite"
    aria-busy="true"
    className="flex items-center justify-center p-8"
  >
    <Spinner />
    <span className="sr-only">Loading sources...</span>
  </div>
)}

{error && (
  <Alert variant="danger" role="alert">
    <p>{error.message}</p>
    <Button onClick={retry}>Try Again</Button>
  </Alert>
)}

{sources.length === 0 && !isLoading && (
  <div role="status" className="text-center py-12">
    <p>No sources found</p>
  </div>
)}
```

---

## WEEK 3: INTERACTIVE COMPONENTS

### Task 1: Dropdown Menus

Make dropdowns keyboard accessible:

```typescript
function Dropdown({ trigger, items }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  
  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-controls="dropdown-menu"
      >
        {trigger}
      </button>
      
      {isOpen && (
        <div
          id="dropdown-menu"
          role="menu"
          className="absolute top-full mt-1 bg-card border rounded-lg shadow-lg"
        >
          {items.map((item, index) => (
            <button
              key={index}
              role="menuitem"
              onClick={() => {
                item.onClick();
                setIsOpen(false);
                buttonRef.current?.focus();
              }}
              className="w-full text-left px-4 py-2 hover:bg-muted"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### Task 2: Tabs

Make tab components accessible:

```typescript
function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div>
      <div role="tablist" aria-label="Settings sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            onClick={() => onChange(tab.id)}
            className={cn(
              'px-4 py-2',
              activeTab === tab.id && 'border-b-2 border-primary'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={activeTab !== tab.id}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
```

---

### Task 3: Tooltips

Make tooltips accessible:

```typescript
function Tooltip({ children, content }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();
  
  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        aria-describedby={isVisible ? tooltipId : undefined}
      >
        {children}
      </div>
      
      {isVisible && (
        <div
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-sm rounded whitespace-nowrap"
        >
          {content}
        </div>
      )}
    </div>
  );
}
```

---

### Task 4: Live Regions

Announce dynamic updates:

```typescript
function JobDetail() {
  const [status, setStatus] = useState('');
  
  return (
    <div>
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        Job status: {status}
      </div>
      
      <StatusBadge status={status} />
    </div>
  );
}
```

---

## TESTING PROTOCOL

### Automated Testing

```bash
# Run ESLint
npm run lint

# Check for accessibility issues
npx eslint --ext .tsx --fix frontend/src/

# Run axe in browser
# Install axe DevTools extension
```

### Manual Testing

**Keyboard Navigation:**
- [ ] Tab through entire page
- [ ] Activate all buttons (Enter/Space)
- [ ] Navigate dropdowns (Arrow keys)
- [ ] Close modals (Escape)
- [ ] No keyboard traps

**Screen Reader:**
- [ ] All content announced
- [ ] Forms have labels
- [ ] Errors announced
- [ ] Loading states announced
- [ ] Landmarks recognized

**Zoom:**
- [ ] Readable at 200% zoom
- [ ] No horizontal scroll
- [ ] All content accessible

---

## COMMIT MESSAGES

```bash
# Week 2
git commit -m "feat: add page-level accessibility (Phase 4 Week 2)

- Unique page titles for all 23 pages
- Proper heading hierarchy (h1 → h2 → h3)
- Form labels and ARIA attributes
- Table semantic markup
- Image alt text
- Loading/error state announcements

WCAG 2.1 AA: Perceivable, Understandable"

# Week 3
git commit -m "feat: interactive component accessibility (Phase 4 Week 3)

- Dropdown keyboard navigation
- Tab component ARIA roles
- Tooltip accessibility
- Live regions for updates
- Focus management

WCAG 2.1 AA: Operable, Robust"
```

---

## SUCCESS CRITERIA

Weeks 2-3 complete when:

- [ ] All pages have unique titles
- [ ] Heading hierarchy correct
- [ ] All forms accessible
- [ ] All tables semantic
- [ ] All images have alt text
- [ ] Loading states announced
- [ ] Dropdowns keyboard accessible
- [ ] Tabs keyboard accessible
- [ ] Tooltips accessible
- [ ] Live regions working
- [ ] ESLint passing
- [ ] Manual testing complete

---

Ready to implement page-level accessibility! ♿
