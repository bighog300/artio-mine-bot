# CODEX: Execute Phase 3, Week 3 - Mobile Responsive Operational Pages

## CONTEXT

You are executing **Phase 3, Week 3** of the Mobile Responsive implementation for Artio Mine Bot.

**Goal:** Optimize operational/monitoring pages for mobile devices.

**Timeline:** Week 3 (3-4 hours)

**Prerequisites:**
- ✅ Week 1 complete (foundation)
- ✅ Week 2 complete (core pages)
- ✅ Mobile patterns established

**Target State:**
- Jobs, Workers, Queues mobile-optimized
- JobDetail mobile-friendly
- Logs readable on mobile
- SourceOperations mobile-accessible
- SourceMapping usable on mobile
- Backfill mobile-optimized

**Pages to Optimize (8 pages):**
1. Jobs (79 lines)
2. Workers (46 lines)
3. Queues (77 lines)
4. JobDetail (105 lines)
5. Logs (288 lines)
6. Backfill (197 lines)
7. SourceOperations (184 lines)
8. SourceMapping (319 lines)

---

## OPTIMIZATION STRATEGY

### Operational Pages Characteristics

**Common patterns:**
- Tables with many columns
- Status indicators
- Time-based data
- Real-time updates
- Action buttons

**Mobile approach:**
- Cards for list views
- Expandable details
- Compact status displays
- Easy-to-tap actions
- Scrollable content

---

## PAGE 1: JOBS (79 lines)

### Mobile Card Implementation

**File:** `frontend/src/pages/Jobs.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Jobs() {
  const isMobile = useIsMobile();
  // ... existing state
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Jobs</h1>
        <Button fullWidth className="sm:w-auto" onClick={() => navigate('/jobs/new')}>
          <Plus className="h-4 w-4" />
          New Job
        </Button>
      </div>
      
      {isMobile ? (
        <div className="space-y-3">
          {jobs.map(job => (
            <JobMobileCard key={job.id} job={job} />
          ))}
        </div>
      ) : (
        <Table>
          {/* Existing table */}
        </Table>
      )}
    </div>
  );
}

function JobMobileCard({ job }: { job: Job }) {
  const navigate = useNavigate();
  
  return (
    <MobileCard onClick={() => navigate(`/jobs/${job.id}`)}>
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium text-foreground">{job.name}</h3>
        <StatusBadge status={job.status} />
      </div>
      
      <JobProgressBar progress={job.progress} className="mb-3" />
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <MobileCardRow label="Type" value={job.job_type} />
        <MobileCardRow label="Source" value={job.source_name} />
        <MobileCardRow label="Started" value={formatDate(job.started_at)} />
        <MobileCardRow label="Duration" value={formatDuration(job.duration)} />
      </div>
    </MobileCard>
  );
}
```

---

## PAGE 2: WORKERS (46 lines)

### Mobile Card Implementation

**File:** `frontend/src/pages/Workers.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Workers() {
  const isMobile = useIsMobile();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Workers</h1>
      
      {isMobile ? (
        <div className="space-y-3">
          {workers.map(worker => (
            <WorkerMobileCard key={worker.id} worker={worker} />
          ))}
        </div>
      ) : (
        <Table>
          {/* Existing table */}
        </Table>
      )}
    </div>
  );
}

function WorkerMobileCard({ worker }: { worker: Worker }) {
  return (
    <MobileCard>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-foreground">{worker.name}</h3>
          <p className="text-sm text-muted-foreground">{worker.hostname}</p>
        </div>
        <HeartbeatBadge lastSeen={worker.last_heartbeat} />
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <MobileCardRow label="Current Job" value={worker.current_job || 'Idle'} />
        <MobileCardRow label="Jobs Completed" value={worker.jobs_completed} />
        <MobileCardRow label="Uptime" value={formatUptime(worker.started_at)} />
        <MobileCardRow label="Queue" value={worker.queue_name} />
      </div>
    </MobileCard>
  );
}
```

---

## PAGE 3: QUEUES (77 lines)

### Mobile Card Implementation

**File:** `frontend/src/pages/Queues.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Queues() {
  const isMobile = useIsMobile();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Queues</h1>
      
      {isMobile ? (
        <div className="space-y-3">
          {queues.map(queue => (
            <QueueMobileCard key={queue.name} queue={queue} />
          ))}
        </div>
      ) : (
        <Table>
          {/* Existing table */}
        </Table>
      )}
    </div>
  );
}

function QueueMobileCard({ queue }: { queue: Queue }) {
  return (
    <MobileCard>
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-medium text-foreground text-lg">{queue.name}</h3>
        <Badge variant={queue.size > 100 ? 'warning' : 'secondary'}>
          {queue.size} jobs
        </Badge>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <MobileCardRow label="Waiting" value={queue.waiting} />
        <MobileCardRow label="Processing" value={queue.processing} />
        <MobileCardRow label="Failed" value={queue.failed} />
        <MobileCardRow label="Workers" value={queue.worker_count} />
      </div>
      
      {queue.size > 0 && (
        <Button variant="outline" size="sm" fullWidth>
          View Jobs
        </Button>
      )}
    </MobileCard>
  );
}
```

---

## PAGE 4: JOBDETAIL (105 lines)

### Mobile Optimization

**File:** `frontend/src/pages/JobDetail.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function JobDetail() {
  const isMobile = useIsMobile();
  const { id } = useParams();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/jobs')}
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>
        </div>
        
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
              {job?.name}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {job?.job_type} • Started {formatDate(job?.started_at)}
            </p>
          </div>
          <div className="flex gap-2">
            <StatusBadge status={job?.status} />
            {job?.status === 'running' && (
              <Button variant="danger" size="sm" onClick={handleCancel}>
                Cancel
              </Button>
            )}
          </div>
        </div>
      </div>
      
      {/* Progress */}
      <div className="bg-card rounded-lg border border-border p-4 lg:p-6">
        <h2 className="text-lg font-semibold mb-3 text-foreground">Progress</h2>
        <JobProgressBar 
          progress={job?.progress || 0} 
          className="mb-3"
        />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-muted-foreground">Pages</div>
            <div className="text-lg font-semibold text-foreground">
              {job?.pages_processed}/{job?.total_pages}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Records</div>
            <div className="text-lg font-semibold text-foreground">
              {job?.records_created}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Errors</div>
            <div className="text-lg font-semibold text-foreground">
              {job?.error_count}
            </div>
          </div>
          <div>
            <div className="text-muted-foreground">Duration</div>
            <div className="text-lg font-semibold text-foreground">
              {formatDuration(job?.duration)}
            </div>
          </div>
        </div>
      </div>
      
      {/* Timeline - Stack on mobile */}
      <div className="bg-card rounded-lg border border-border p-4 lg:p-6">
        <h2 className="text-lg font-semibold mb-4 text-foreground">Timeline</h2>
        <JobEventTimeline events={job?.events || []} />
      </div>
    </div>
  );
}
```

---

## PAGE 5: LOGS (288 lines)

### Mobile Optimization - Virtual Scroll Preserved

**File:** `frontend/src/pages/Logs.tsx`

**Key changes:**
1. Compact filters on mobile
2. Smaller log entries
3. Preserve virtual scrolling
4. Touch-friendly controls

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Logs() {
  const isMobile = useIsMobile();
  
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header - Compact on mobile */}
      <div className="flex flex-col gap-3 mb-4">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">Logs</h1>
        
        {/* Filters - Collapsible on mobile */}
        <div className="flex flex-col sm:flex-row gap-2">
          <Input
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-64"
          />
          <Select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            options={levelOptions}
            className="w-full sm:w-48"
          />
          <Button
            variant="outline"
            size={isMobile ? 'md' : 'sm'}
            onClick={clearLogs}
            className="w-full sm:w-auto"
          >
            Clear
          </Button>
        </div>
      </div>
      
      {/* Log entries - Virtual scroll */}
      <div className="flex-1 overflow-auto bg-card rounded-lg border border-border">
        <div style={{ height: logs.length * (isMobile ? 60 : 48) }}>
          {visibleLogs.map((log, index) => (
            <div
              key={log.id}
              className={cn(
                'px-3 py-2 lg:px-4 lg:py-2 border-b border-border text-xs lg:text-sm font-mono',
                index % 2 === 0 ? 'bg-background' : 'bg-muted/20'
              )}
              style={{
                position: 'absolute',
                top: index * (isMobile ? 60 : 48),
                left: 0,
                right: 0,
              }}
            >
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground text-xs">
                  {formatTime(log.timestamp)}
                </span>
                <Badge 
                  variant={getLevelVariant(log.level)}
                  className="w-fit"
                >
                  {log.level}
                </Badge>
                <span className="text-foreground break-all sm:break-normal">
                  {log.message}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## PAGE 6: BACKFILL (197 lines)

### Mobile Optimization

**File:** `frontend/src/pages/Backfill.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function Backfill() {
  const isMobile = useIsMobile();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
          Backfill Campaigns
        </h1>
        <Button 
          fullWidth
          className="sm:w-auto"
          onClick={() => setShowCreateDialog(true)}
        >
          <Plus className="h-4 w-4" />
          New Campaign
        </Button>
      </div>
      
      {isMobile ? (
        <div className="space-y-3">
          {campaigns.map(campaign => (
            <BackfillMobileCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {campaigns.map(campaign => (
            <BackfillCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      )}
    </div>
  );
}

function BackfillMobileCard({ campaign }: { campaign: Campaign }) {
  return (
    <MobileCard>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-foreground">{campaign.name}</h3>
          <p className="text-sm text-muted-foreground">
            {campaign.source_count} sources
          </p>
        </div>
        <StatusBadge status={campaign.status} />
      </div>
      
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-muted-foreground">Progress</span>
          <span className="text-foreground font-medium">
            {campaign.progress}%
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className="bg-primary h-2 rounded-full transition-all"
            style={{ width: `${campaign.progress}%` }}
          />
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <MobileCardRow label="Schedule" value={campaign.schedule} />
        <MobileCardRow label="Next Run" value={formatDate(campaign.next_run)} />
      </div>
    </MobileCard>
  );
}
```

---

## PAGE 7: SOURCEOPERATIONS (184 lines)

### Mobile Optimization - Console Output

**File:** `frontend/src/pages/SourceOperations.tsx`

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function SourceOperations() {
  const isMobile = useIsMobile();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
        Source Operations
      </h1>
      
      {/* Operation selector */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Button
          variant={selectedOp === 'crawl' ? 'primary' : 'outline'}
          onClick={() => setSelectedOp('crawl')}
          fullWidth
        >
          Crawl
        </Button>
        <Button
          variant={selectedOp === 'extract' ? 'primary' : 'outline'}
          onClick={() => setSelectedOp('extract')}
          fullWidth
        >
          Extract
        </Button>
        <Button
          variant={selectedOp === 'sync' ? 'primary' : 'outline'}
          onClick={() => setSelectedOp('sync')}
          fullWidth
        >
          Sync
        </Button>
        <Button
          variant={selectedOp === 'validate' ? 'primary' : 'outline'}
          onClick={() => setSelectedOp('validate')}
          fullWidth
        >
          Validate
        </Button>
      </div>
      
      {/* Source selector */}
      <Select
        label="Source"
        value={selectedSource}
        onChange={(e) => setSelectedSource(e.target.value)}
        options={sourceOptions}
      />
      
      {/* Action button */}
      <Button
        fullWidth
        className="sm:w-auto"
        onClick={handleExecute}
        disabled={!selectedSource || isRunning}
      >
        {isRunning ? (
          <>
            <Spinner size="sm" />
            Running...
          </>
        ) : (
          `Execute ${selectedOp}`
        )}
      </Button>
      
      {/* Console output - Scrollable */}
      <div className="bg-gray-900 rounded-lg p-3 lg:p-4 min-h-[300px] max-h-[500px] overflow-auto">
        <pre className="text-xs lg:text-sm text-gray-100 font-mono whitespace-pre-wrap break-words">
          {consoleOutput || 'No output yet. Select an operation and execute.'}
        </pre>
      </div>
    </div>
  );
}
```

---

## PAGE 8: SOURCEMAPPING (319 lines)

### Mobile Optimization - Complex UI

**File:** `frontend/src/pages/SourceMapping.tsx`

**Strategy:**
- Stack panels vertically on mobile
- Make mapping matrix scrollable
- Simplify controls

```typescript
import { useIsMobile } from '@/lib/mobile-utils';

export function SourceMapping() {
  const isMobile = useIsMobile();
  
  return (
    <div className="space-y-4 lg:space-y-6">
      <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
        Source Mapping
      </h1>
      
      {/* Layout: Stack on mobile, side-by-side on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Page type sidebar */}
        <div className="lg:col-span-3">
          <PageTypeSidebar
            selectedType={selectedType}
            onSelectType={setSelectedType}
          />
        </div>
        
        {/* Main mapping area */}
        <div className="lg:col-span-9 space-y-4">
          {/* Preset panel - Collapsible on mobile */}
          {(!isMobile || showPresets) && (
            <MappingPresetPanel
              presets={presets}
              onApplyPreset={handleApplyPreset}
            />
          )}
          
          {isMobile && (
            <Button
              variant="outline"
              fullWidth
              onClick={() => setShowPresets(!showPresets)}
            >
              {showPresets ? 'Hide' : 'Show'} Presets
            </Button>
          )}
          
          {/* Mapping matrix - Scrollable */}
          <div className="overflow-x-auto -mx-4 px-4 lg:mx-0 lg:px-0">
            <MappingMatrix
              fields={fields}
              mappings={mappings}
              onUpdateMapping={handleUpdateMapping}
            />
          </div>
          
          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-2 sm:justify-end">
            <Button
              variant="outline"
              fullWidth
              className="sm:w-auto"
              onClick={handleReset}
            >
              Reset
            </Button>
            <Button
              fullWidth
              className="sm:w-auto"
              onClick={handleSave}
            >
              Save Mapping
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## TESTING CHECKLIST

### All Operational Pages

- [ ] Jobs: Cards on mobile, table on desktop
- [ ] Workers: Status clearly visible
- [ ] Queues: Job counts readable
- [ ] JobDetail: Progress bar visible
- [ ] Logs: Virtual scroll works
- [ ] Backfill: Campaigns accessible
- [ ] SourceOps: Console readable
- [ ] SourceMapping: Matrix scrollable

### Mobile Specific

- [ ] No horizontal scroll (except intended)
- [ ] All text readable (12px minimum)
- [ ] Touch targets 44px minimum
- [ ] Buttons full-width on mobile
- [ ] Proper spacing
- [ ] Dark mode works
- [ ] Transitions smooth

### Functionality

- [ ] All actions work on mobile
- [ ] Status updates reflect
- [ ] Real-time data updates
- [ ] Navigation works
- [ ] Filters apply correctly

---

## COMMIT STRATEGY

```bash
# Jobs, Workers, Queues
git add frontend/src/pages/{Jobs,Workers,Queues}.tsx
git commit -m "feat: optimize Jobs, Workers, Queues for mobile

- Mobile card views for list pages
- Status badges visible in cards
- Touch-friendly actions
- Responsive grids

All operational monitoring accessible on mobile"

# JobDetail, Logs
git add frontend/src/pages/{JobDetail,Logs}.tsx
git commit -m "feat: optimize JobDetail and Logs for mobile

JobDetail:
- Stacked layout on mobile
- Progress metrics grid
- Timeline readable

Logs:
- Compact filters
- Virtual scroll preserved
- Smaller entries on mobile

Real-time monitoring works on mobile"

# Backfill, SourceOps, SourceMapping
git add frontend/src/pages/{Backfill,SourceOperations,SourceMapping}.tsx
git commit -m "feat: optimize Backfill, SourceOps, SourceMapping for mobile

Backfill:
- Campaign cards mobile-friendly
- Progress bars visible

SourceOps:
- Full-width operation buttons
- Scrollable console output

SourceMapping:
- Stacked vertical layout
- Scrollable mapping matrix
- Collapsible panels

All advanced features accessible on mobile"
```

---

## SUCCESS CRITERIA

Week 3 is complete when:

- [ ] All 8 operational pages mobile-optimized
- [ ] Card views implemented where needed
- [ ] Complex UIs handled (logs, mapping)
- [ ] All functionality preserved
- [ ] Tested at multiple breakpoints
- [ ] No regressions on desktop
- [ ] Build successful
- [ ] Committed to git

---

Ready to optimize operational pages! 🔧📱
