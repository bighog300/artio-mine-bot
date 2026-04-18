# CODEX: Execute Phase 3, Week 2 - Mobile Responsive Core Pages

## CONTEXT

You are executing **Phase 3, Week 2** of the Mobile Responsive implementation for Artio Mine Bot.

**Goal:** Optimize the 3 most important pages for mobile devices (Dashboard, Sources, Records).

**Timeline:** Week 2 (3-4 hours)

**Prerequisites:**
- ✅ Week 1 complete (mobile navigation, utilities, components)
- ✅ MobileNav component working
- ✅ MobileCard component available
- ✅ ResponsiveGrid component available
- ✅ Mobile utilities (useIsMobile, useViewport) ready

**Target State:**
- Dashboard works beautifully on mobile
- Sources page mobile-optimized
- Records page mobile-optimized
- Touch-friendly interactions
- Responsive layouts
- Professional mobile experience

---

## MOBILE OPTIMIZATION STRATEGY

### Core Principles

1. **Mobile-First Layout**
   - Start with mobile design
   - Add complexity as screen grows
   - Stack vertically on small screens

2. **Touch-Friendly**
   - Large buttons (44px minimum)
   - Adequate spacing
   - Easy tap targets

3. **Content Priority**
   - Show most important info first
   - Hide/collapse secondary info
   - Progressive disclosure

4. **Performance**
   - Minimize re-renders
   - Lazy load when needed
   - Optimize images

---

## PAGE 1: DASHBOARD (187 lines)

### Current Issues on Mobile

```
❌ StatCards too small
❌ Metrics cramped
❌ Charts overflow
❌ Grid too tight
❌ Navigation cluttered
```

### Target Mobile Experience

```
✅ Large, tappable cards
✅ Stacked vertical layout
✅ Readable metrics
✅ Charts scale properly
✅ Clean spacing
```

---

### Implementation

**File:** `frontend/src/pages/Dashboard.tsx`

#### Step 1: Update Page Container

**Before:**
```typescript
<div className="space-y-6">
  <h1 className="text-3xl font-bold">Dashboard</h1>
  {/* Content */}
</div>
```

**After:**
```typescript
<div className="space-y-4 lg:space-y-6">
  <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
    Dashboard
  </h1>
  {/* Content */}
</div>
```

**Changes:**
- Reduce vertical spacing on mobile (`space-y-4` → `lg:space-y-6`)
- Smaller heading on mobile (`text-2xl` → `lg:text-3xl`)

---

#### Step 2: Optimize StatCard Grid

**Before:**
```typescript
<div className="grid grid-cols-4 gap-4">
  <StatCard label="Total Sources" value={stats.sources} />
  <StatCard label="Total Records" value={stats.records} />
  <StatCard label="Active Jobs" value={stats.jobs} />
  <StatCard label="Workers" value={stats.workers} />
</div>
```

**After:**
```typescript
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
  <StatCard label="Total Sources" value={stats.sources} />
  <StatCard label="Total Records" value={stats.records} />
  <StatCard label="Active Jobs" value={stats.jobs} />
  <StatCard label="Workers" value={stats.workers} />
</div>
```

**Changes:**
- 1 column on mobile
- 2 columns on tablets (sm:)
- 4 columns on desktop (lg:)
- Smaller gap on mobile

---

#### Step 3: Update StatCard Component

**Find the StatCard component definition (usually in same file):**

**Before:**
```typescript
function StatCard({ label, value, trend }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="text-sm text-gray-600">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}
```

**After:**
```typescript
function StatCard({ label, value, trend }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-4 lg:p-6">
      <div className="text-sm text-muted-foreground font-medium">{label}</div>
      <div className="text-3xl lg:text-4xl font-bold mt-2 text-foreground">
        {value?.toLocaleString() || '0'}
      </div>
      {trend && (
        <div className={cn(
          "text-sm mt-2",
          trend > 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
        )}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
        </div>
      )}
    </div>
  );
}
```

**Changes:**
- Use semantic colors (bg-card, text-foreground)
- Larger value text (better readability)
- More padding on desktop
- Format numbers with commas
- Add optional trend indicator

---

#### Step 4: Optimize Quick Actions

**Before:**
```typescript
<div className="flex gap-4">
  <Button onClick={() => navigate('/sources/new')}>
    Add Source
  </Button>
  <Button onClick={() => navigate('/jobs')}>
    View Jobs
  </Button>
  <Button onClick={() => navigate('/records')}>
    Browse Records
  </Button>
</div>
```

**After:**
```typescript
<div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
  <Button 
    fullWidth
    className="sm:w-auto"
    onClick={() => navigate('/sources/new')}
  >
    <Plus className="h-4 w-4" />
    Add Source
  </Button>
  <Button 
    fullWidth
    variant="secondary"
    className="sm:w-auto"
    onClick={() => navigate('/jobs')}
  >
    View Jobs
  </Button>
  <Button 
    fullWidth
    variant="secondary"
    className="sm:w-auto"
    onClick={() => navigate('/records')}
  >
    Browse Records
  </Button>
</div>
```

**Changes:**
- Stack vertically on mobile (`flex-col`)
- Horizontal on tablets+ (`sm:flex-row`)
- Full width buttons on mobile
- Auto width on desktop
- Add icons for clarity

---

#### Step 5: Optimize Recent Activity Section

**Before:**
```typescript
<div className="bg-white rounded-lg border p-6">
  <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
  <div className="space-y-3">
    {activities.map(activity => (
      <div key={activity.id} className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded">
        <div className="text-sm text-gray-600">{activity.time}</div>
        <div className="flex-1 text-sm">{activity.description}</div>
      </div>
    ))}
  </div>
</div>
```

**After:**
```typescript
<div className="bg-card rounded-lg border border-border p-4 lg:p-6">
  <h2 className="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-foreground">
    Recent Activity
  </h2>
  <div className="space-y-2 lg:space-y-3">
    {activities.map(activity => (
      <div 
        key={activity.id} 
        className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 p-3 hover:bg-muted/40 rounded active:bg-muted/60 transition-colors"
      >
        <div className="text-xs sm:text-sm text-muted-foreground">
          {activity.time}
        </div>
        <div className="flex-1 text-sm text-foreground">
          {activity.description}
        </div>
      </div>
    ))}
  </div>
</div>
```

**Changes:**
- Stack time/description on mobile
- Semantic colors
- Touch feedback (active:)
- Responsive text sizes
- Better spacing

---

## PAGE 2: SOURCES (276 lines)

### Current Issues on Mobile

```
❌ Table too wide
❌ Many columns overflow
❌ Action buttons too small
❌ Filter controls cramped
❌ Can't see full URLs
```

### Target Mobile Experience

```
✅ Card view instead of table
✅ Most important info visible
✅ Easy to tap actions
✅ Compact filters
✅ Scrollable if needed
```

---

### Implementation

**File:** `frontend/src/pages/Sources.tsx`

#### Step 1: Add Mobile Detection

**At top of component:**

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Sources() {
  const isMobile = useIsMobile();
  const [sources, setSources] = useState([]);
  // ... rest of state
```

---

#### Step 2: Create Mobile Card View

**Add this component inside Sources.tsx:**

```typescript
function SourceMobileCard({ source }: { source: Source }) {
  const navigate = useNavigate();
  
  return (
    <MobileCard 
      onClick={() => navigate(`/sources/${source.id}`)}
      className="cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-foreground truncate">
            {source.name}
          </h3>
          <p className="text-sm text-muted-foreground truncate mt-1">
            {source.url}
          </p>
        </div>
        <StatusBadge status={source.status} />
      </div>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <MobileCardRow 
          label="Pages" 
          value={source.page_count || 0} 
        />
        <MobileCardRow 
          label="Records" 
          value={source.record_count || 0} 
        />
        <MobileCardRow 
          label="Last Crawl" 
          value={source.last_crawl ? formatDate(source.last_crawl) : 'Never'} 
        />
        <MobileCardRow 
          label="Type" 
          value={source.source_type} 
        />
      </div>
    </MobileCard>
  );
}
```

---

#### Step 3: Update Main Render - Conditional View

**Before:**
```typescript
return (
  <div className="space-y-6">
    <div className="flex justify-between items-center">
      <h1 className="text-3xl font-bold">Sources</h1>
      <Button onClick={() => setShowCreateDialog(true)}>
        Add Source
      </Button>
    </div>
    
    {/* Filters */}
    <div className="flex gap-4">
      {/* Filter controls */}
    </div>
    
    {/* Table */}
    <Table>
      {/* Table content */}
    </Table>
  </div>
);
```

**After:**
```typescript
return (
  <div className="space-y-4 lg:space-y-6">
    {/* Header */}
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
        Sources
      </h1>
      <Button 
        fullWidth
        className="sm:w-auto"
        onClick={() => setShowCreateDialog(true)}
      >
        <Plus className="h-4 w-4" />
        Add Source
      </Button>
    </div>
    
    {/* Filters - Compact on mobile */}
    <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
      <Input
        placeholder="Search sources..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full sm:w-64"
      />
      <Select
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        options={statusOptions}
        className="w-full sm:w-48"
      />
    </div>
    
    {/* Conditional render: Mobile cards or Desktop table */}
    {isMobile ? (
      <div className="space-y-3">
        {sources.map(source => (
          <SourceMobileCard key={source.id} source={source} />
        ))}
      </div>
    ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>URL</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Pages</TableHead>
            <TableHead>Records</TableHead>
            <TableHead>Last Crawl</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sources.map(source => (
            <TableRow key={source.id}>
              <TableCell>{source.name}</TableCell>
              <TableCell>{source.url}</TableCell>
              <TableCell><StatusBadge status={source.status} /></TableCell>
              <TableCell>{source.page_count}</TableCell>
              <TableCell>{source.record_count}</TableCell>
              <TableCell>{formatDate(source.last_crawl)}</TableCell>
              <TableCell>
                <IconButton onClick={() => navigate(`/sources/${source.id}`)}>
                  <Eye className="h-4 w-4" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )}
    
    {/* Empty state */}
    {sources.length === 0 && (
      <div className="text-center py-12 text-muted-foreground">
        No sources found
      </div>
    )}
  </div>
);
```

**Changes:**
- Mobile detection with `useIsMobile()`
- Card view for mobile
- Table view for desktop
- Responsive header
- Compact filters
- Full-width button on mobile

---

## PAGE 3: RECORDS (266 lines)

### Current Issues on Mobile

```
❌ Table too wide (many columns)
❌ Images too small
❌ Filter bar cluttered
❌ Can't see confidence scores well
❌ Actions hard to tap
```

### Target Mobile Experience

```
✅ Card view with images
✅ Key info visible
✅ Confidence bars clear
✅ Easy tap actions
✅ Simple filters
```

---

### Implementation

**File:** `frontend/src/pages/Records.tsx`

#### Step 1: Add Mobile Detection

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Records() {
  const isMobile = useIsMobile();
  // ... rest of state
```

---

#### Step 2: Create Mobile Card View

```typescript
function RecordMobileCard({ record }: { record: Record }) {
  const navigate = useNavigate();
  
  return (
    <MobileCard 
      onClick={() => navigate(`/records/${record.id}`)}
      className="cursor-pointer"
    >
      <div className="flex gap-3">
        {/* Image thumbnail */}
        {record.image_urls?.[0] && (
          <img
            src={record.image_urls[0]}
            alt={record.title}
            className="w-20 h-20 object-cover rounded border border-border flex-shrink-0"
          />
        )}
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-medium text-foreground line-clamp-2">
              {record.title}
            </h3>
            <RecordTypeBadge type={record.record_type} />
          </div>
          
          {/* Confidence */}
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-medium text-foreground">
                {Math.round((record.confidence || 0) * 100)}%
              </span>
            </div>
            <ConfidenceBar value={record.confidence || 0} />
          </div>
          
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-muted-foreground">Source:</span>{' '}
              <span className="text-foreground">{record.source_name}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Created:</span>{' '}
              <span className="text-foreground">{formatDate(record.created_at)}</span>
            </div>
          </div>
        </div>
      </div>
    </MobileCard>
  );
}
```

---

#### Step 3: Update Main Render

**Before:**
```typescript
return (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold">Records</h1>
    
    {/* Filters */}
    <div className="flex gap-4">
      {/* Many filter controls */}
    </div>
    
    {/* Table */}
    <Table>
      {/* Table with many columns */}
    </Table>
  </div>
);
```

**After:**
```typescript
return (
  <div className="space-y-4 lg:space-y-6">
    {/* Header */}
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
        Records
      </h1>
      <div className="flex gap-2 w-full sm:w-auto">
        <Button 
          fullWidth
          variant="secondary"
          className="sm:w-auto"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="primary" className="ml-2">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
        <Button 
          fullWidth
          className="sm:w-auto"
          onClick={() => navigate('/records/new')}
        >
          <Plus className="h-4 w-4" />
          Add
        </Button>
      </div>
    </div>
    
    {/* Collapsible Filters on Mobile */}
    {(showFilters || !isMobile) && (
      <div className="bg-card rounded-lg border border-border p-4 space-y-3">
        <Input
          placeholder="Search records..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <Select
            label="Type"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            options={typeOptions}
          />
          <Select
            label="Source"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            options={sourceOptions}
          />
          <Select
            label="Confidence"
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(e.target.value)}
            options={confidenceOptions}
          />
          <Button 
            variant="ghost"
            onClick={clearFilters}
            className="sm:mt-6"
          >
            Clear All
          </Button>
        </div>
      </div>
    )}
    
    {/* Conditional render */}
    {isMobile ? (
      <div className="space-y-3">
        {records.map(record => (
          <RecordMobileCard key={record.id} record={record} />
        ))}
      </div>
    ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Image</TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map(record => (
            <TableRow key={record.id}>
              <TableCell>
                {record.image_urls?.[0] && (
                  <img 
                    src={record.image_urls[0]} 
                    className="w-12 h-12 object-cover rounded border border-border"
                    alt=""
                  />
                )}
              </TableCell>
              <TableCell>{record.title}</TableCell>
              <TableCell><RecordTypeBadge type={record.record_type} /></TableCell>
              <TableCell>{record.source_name}</TableCell>
              <TableCell><ConfidenceBadge value={record.confidence} /></TableCell>
              <TableCell>{formatDate(record.created_at)}</TableCell>
              <TableCell>
                <IconButton onClick={() => navigate(`/records/${record.id}`)}>
                  <Eye className="h-4 w-4" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )}
    
    {/* Pagination */}
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
      <div className="text-sm text-muted-foreground">
        Showing {records.length} of {totalRecords} records
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(page - 1)}
          disabled={page === 1}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage(page + 1)}
          disabled={page * pageSize >= totalRecords}
        >
          Next
        </Button>
      </div>
    </div>
  </div>
);
```

**Changes:**
- Mobile card view with images
- Collapsible filters on mobile
- Filter toggle button with count
- Responsive header
- Pagination stacked on mobile
- Confidence bars in cards

---

## TESTING CHECKLIST

After implementing mobile optimizations:

### Dashboard
- [ ] StatCards stack on mobile (1 column)
- [ ] StatCards show 2 columns on tablet
- [ ] StatCards show 4 columns on desktop
- [ ] Metrics readable on small screens
- [ ] Action buttons full-width on mobile
- [ ] Quick actions stack vertically
- [ ] Recent activity readable

### Sources
- [ ] Cards appear on mobile (< 768px)
- [ ] Table appears on desktop (>= 768px)
- [ ] Search input full-width on mobile
- [ ] Add Source button full-width on mobile
- [ ] Cards are tappable
- [ ] StatusBadge visible in cards
- [ ] All info accessible in cards

### Records
- [ ] Cards appear on mobile
- [ ] Table appears on desktop
- [ ] Images show in cards
- [ ] Confidence bars visible
- [ ] Filters collapsible on mobile
- [ ] Filter button shows count
- [ ] Pagination stacks on mobile
- [ ] Records tappable

### All Pages
- [ ] No horizontal scroll on mobile
- [ ] Touch targets 44px minimum
- [ ] Text readable (not too small)
- [ ] Proper spacing
- [ ] Semantic colors used
- [ ] Dark mode works
- [ ] Smooth transitions

---

## BROWSER TESTING

Test in Chrome DevTools:

```bash
1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Test these sizes:
   - iPhone SE (375px)
   - iPhone 12 Pro (390px)
   - iPad Air (820px)
   - Desktop (1280px)

4. For each page, verify:
   - Layout looks good
   - All content accessible
   - No overflow
   - Buttons tappable
   - Text readable
```

---

## PERFORMANCE TIPS

### Avoid Common Mistakes

**❌ Don't:**
```typescript
// Re-renders on every resize
const isMobile = window.innerWidth < 768;
```

**✅ Do:**
```typescript
// Hook handles resize efficiently
const isMobile = useIsMobile();
```

**❌ Don't:**
```typescript
// Duplicates component logic
{isMobile ? <MobileCard /> : <DesktopCard />}
{isMobile ? <MobileCard /> : <DesktopCard />}
```

**✅ Do:**
```typescript
// Extract to component
<ResponsiveCard isMobile={isMobile} />
```

---

## COMMIT STRATEGY

**Commit after each page:**

```bash
# After Dashboard
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: optimize Dashboard for mobile

- StatCards responsive grid (1/2/4 columns)
- Larger value text for readability
- Full-width buttons on mobile
- Stack quick actions vertically
- Responsive activity section

Mobile-first approach with progressive enhancement"

# After Sources
git add frontend/src/pages/Sources.tsx
git commit -m "feat: optimize Sources page for mobile

- Add SourceMobileCard component
- Card view on mobile, table on desktop
- Conditional rendering with useIsMobile
- Responsive header and filters
- Touch-friendly tap targets

All source info accessible in card format"

# After Records
git add frontend/src/pages/Records.tsx
git commit -m "feat: optimize Records page for mobile

- Add RecordMobileCard with image thumbnails
- Collapsible filters on mobile
- Filter toggle button with active count
- Card view shows confidence bars
- Responsive pagination

Mobile experience matches desktop functionality"
```

---

## FINAL VERIFICATION

After all 3 pages complete:

```bash
# Run build
npm run build

# Check bundle size
du -h dist/

# Run tests (if any)
npm test

# Visual check
npm run dev
# Test each page at 375px, 768px, 1024px
```

---

## SUCCESS CRITERIA

Week 2 is complete when:

- [ ] Dashboard mobile-optimized
- [ ] Sources mobile-optimized
- [ ] Records mobile-optimized
- [ ] All pages tested at multiple breakpoints
- [ ] No horizontal scroll on mobile
- [ ] All content accessible
- [ ] Touch targets 44px+
- [ ] Build successful
- [ ] Committed to git

---

## COMMIT MESSAGE (Week 2 Complete)

```
feat: complete mobile optimization for core pages

Week 2 - Core Pages Mobile Responsive:

Dashboard:
- Responsive StatCard grid (1/2/4 columns)
- Mobile-optimized metrics display
- Stacked action buttons
- Improved readability

Sources:
- Mobile card view with key info
- Desktop table view preserved
- Conditional rendering based on viewport
- Touch-friendly navigation

Records:
- Mobile cards with image thumbnails
- Confidence bars in card view
- Collapsible filter system
- Responsive pagination

All Pages:
- No horizontal scroll on mobile
- Touch targets 44px+ minimum
- Semantic colors throughout
- Dark mode compatible
- Tested at 375px, 768px, 1024px

Closes: Phase 3, Week 2 - Core Pages
```

---

Ready to optimize core pages for mobile! 📱
