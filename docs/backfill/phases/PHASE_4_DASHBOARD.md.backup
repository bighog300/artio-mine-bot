# Phase 4: Frontend Dashboard & UI

## Overview

Phase 4 adds a complete frontend dashboard for the backfill system. Visualize data quality, manage campaigns, monitor progress, and explore analytics through an intuitive web interface.

**Status**: 📋 PLANNED

**Prerequisites**: Phases 1, 2, & 3 must be completed

---

## What Phase 4 Delivers

### 1. Dashboard Overview

**Main Dashboard Page** (`/backfill`):
- Overall statistics (total campaigns, success rate, avg improvement)
- Active campaigns with progress bars
- Recent completions
- Data quality trends chart
- Quick actions (create campaign, view analytics)

### 2. Campaign Management UI

**Campaign List View** (`/backfill/campaigns`):
- Sortable/filterable table of all campaigns
- Status badges (pending, running, completed, failed)
- Progress indicators
- Quick actions (start, pause, delete)

**Campaign Detail View** (`/backfill/campaigns/{id}`):
- Full campaign information
- Job-level breakdown
- Success/failure details
- Before/after completeness comparison
- Individual record improvements

**Campaign Creation Wizard** (`/backfill/campaigns/new`):
- Step 1: Choose strategy (selective, URL-based, time-based, source)
- Step 2: Configure filters (record type, completeness range, etc.)
- Step 3: Set options (limit, priority, auto-start)
- Step 4: Preview records that will be backfilled
- Step 5: Confirm and create

### 3. Data Quality Dashboard

**Completeness Overview** (`/backfill/quality`):
- Completeness distribution chart (how many records at each %)
- Breakdown by record type (artists, events, venues)
- Top incomplete records (candidates for backfill)
- Field-level statistics (which fields are missing most)
- Improvement trends over time

**Quality Metrics**:
- Average completeness score by record type
- Most common missing fields
- Records below quality threshold
- Improvement rate (% gained per week)

### 4. Real-Time Monitoring

**Live Campaign Monitor** (`/backfill/monitor`):
- Active campaigns with live progress bars
- Real-time job completion updates (via WebSocket)
- Success/failure counters
- Current processing speed (records/minute)
- ETA for completion

**Live Updates**:
```javascript
// WebSocket connection
ws://localhost:8765/ws/backfill/campaigns/{id}

// Messages:
{
  "type": "job_completed",
  "job_id": "job-123",
  "record_id": "rec-456",
  "before_completeness": 45,
  "after_completeness": 73,
  "fields_updated": ["bio", "nationality"]
}
```

### 5. Analytics Dashboard

**Analytics Views**:

**Trends** (`/backfill/analytics/trends`):
- Completeness over time (line chart)
- Campaigns run per week (bar chart)
- Success rate trends
- Processing volume

**Performance** (`/backfill/analytics/performance`):
- Average improvement by strategy
- Success rate by record type
- Processing speed by time of day
- Failure analysis (top error types)

**Impact** (`/backfill/analytics/impact`):
- Total records enriched
- Total fields filled
- Top improved records
- Most valuable campaigns

### 6. Schedule Management UI

**Schedules List** (`/backfill/schedules`):
- All scheduled campaigns
- Next run times
- Last execution status
- Enable/disable toggles

**Schedule Editor** (`/backfill/schedules/new`):
- Visual cron builder
- Filter configuration
- Auto-start settings
- Notification setup

### 7. Settings & Configuration

**Backfill Settings** (`/backfill/settings`):
- Default options (limit, priority)
- Notification preferences
- Quality thresholds
- Crawler settings (rate limits, timeouts)
- Webhook configurations

---

## Component Architecture

### React Components

```
frontend/src/components/backfill/
├── BackfillDashboard.tsx          # Main dashboard
├── CampaignList.tsx               # List of all campaigns
├── CampaignDetail.tsx             # Campaign details
├── CampaignWizard.tsx             # Create campaign flow
├── QualityDashboard.tsx           # Data quality overview
├── LiveMonitor.tsx                # Real-time monitoring
├── AnalyticsDashboard.tsx         # Analytics views
├── ScheduleManager.tsx            # Schedule management
└── shared/
    ├── ProgressBar.tsx            # Progress indicator
    ├── StatusBadge.tsx            # Status badges
    ├── CompletenessScore.tsx      # Completeness visualization
    ├── CampaignStats.tsx          # Statistics cards
    └── TrendChart.tsx             # Charts for trends
```

### State Management

```typescript
// Redux store for backfill
interface BackfillState {
  campaigns: {
    items: Campaign[];
    loading: boolean;
    error: string | null;
  };
  activeCampaign: Campaign | null;
  quality: {
    distribution: number[];
    byType: Record<string, number>;
  };
  analytics: {
    trends: TrendData[];
    performance: PerformanceMetrics;
  };
  schedules: Schedule[];
}
```

### API Client

```typescript
// frontend/src/api/backfill.ts

export const backfillApi = {
  // Campaigns
  getCampaigns: () => get('/api/backfill/campaigns'),
  getCampaign: (id: string) => get(`/api/backfill/campaigns/${id}`),
  createCampaign: (data: CreateCampaignRequest) => 
    post('/api/backfill/campaigns', data),
  startCampaign: (id: string) => 
    post(`/api/backfill/campaigns/${id}/start`),
  
  // Preview
  preview: (params: PreviewParams) => 
    get('/api/backfill/preview', { params }),
  
  // Analytics
  getAnalytics: () => get('/api/backfill/analytics/summary'),
  getTrends: (params: TrendParams) => 
    get('/api/backfill/analytics/trends', { params }),
  
  // Schedules
  getSchedules: () => get('/api/backfill/schedules'),
  createSchedule: (data: CreateScheduleRequest) => 
    post('/api/backfill/schedules', data),
};
```

---

## UI Components

### 1. Dashboard Overview

```tsx
// BackfillDashboard.tsx
export function BackfillDashboard() {
  const { data: summary } = useBackfillSummary();
  const { data: activeCampaigns } = useActiveCampaigns();
  
  return (
    <div className="backfill-dashboard">
      {/* Stats Cards */}
      <div className="stats-grid">
        <StatCard 
          title="Total Campaigns"
          value={summary.totalCampaigns}
          trend="+5 this week"
        />
        <StatCard 
          title="Success Rate"
          value={`${summary.successRate}%`}
          trend="+2% vs last week"
        />
        <StatCard 
          title="Avg Improvement"
          value={`+${summary.avgImprovement}%`}
          trend="completeness"
        />
        <StatCard 
          title="Records Enriched"
          value={summary.totalRecords}
          trend="all time"
        />
      </div>
      
      {/* Active Campaigns */}
      <div className="active-campaigns">
        <h2>Active Campaigns</h2>
        {activeCampaigns.map(campaign => (
          <CampaignCard key={campaign.id} campaign={campaign} />
        ))}
      </div>
      
      {/* Completeness Trend Chart */}
      <div className="trend-chart">
        <h2>Data Quality Trends</h2>
        <CompletenessChart data={summary.trends} />
      </div>
      
      {/* Quick Actions */}
      <div className="quick-actions">
        <Button onClick={() => navigate('/backfill/campaigns/new')}>
          Create Campaign
        </Button>
        <Button onClick={() => navigate('/backfill/quality')}>
          View Quality Report
        </Button>
      </div>
    </div>
  );
}
```

### 2. Campaign Creation Wizard

```tsx
// CampaignWizard.tsx
export function CampaignWizard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<CampaignFormData>({});
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  
  const steps = [
    { id: 1, title: "Strategy", component: StrategyStep },
    { id: 2, title: "Filters", component: FiltersStep },
    { id: 3, title: "Options", component: OptionsStep },
    { id: 4, title: "Preview", component: PreviewStep },
    { id: 5, title: "Confirm", component: ConfirmStep },
  ];
  
  return (
    <div className="campaign-wizard">
      <WizardSteps steps={steps} currentStep={step} />
      
      <div className="wizard-content">
        {step === 1 && (
          <StrategyStep 
            value={formData.strategy}
            onChange={(strategy) => setFormData({...formData, strategy})}
          />
        )}
        {step === 2 && (
          <FiltersStep 
            value={formData.filters}
            strategy={formData.strategy}
            onChange={(filters) => setFormData({...formData, filters})}
          />
        )}
        {/* ... other steps */}
      </div>
      
      <div className="wizard-actions">
        {step > 1 && (
          <Button onClick={() => setStep(step - 1)}>Back</Button>
        )}
        {step < 5 && (
          <Button onClick={() => setStep(step + 1)}>Next</Button>
        )}
        {step === 5 && (
          <Button onClick={handleCreate}>Create Campaign</Button>
        )}
      </div>
    </div>
  );
}
```

### 3. Live Monitor

```tsx
// LiveMonitor.tsx
export function LiveMonitor() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  
  useEffect(() => {
    // WebSocket connection
    const ws = new WebSocket('ws://localhost:8765/ws/backfill/live');
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      setCampaigns(prev => prev.map(c => 
        c.id === update.campaign_id 
          ? { ...c, ...update }
          : c
      ));
    };
    
    return () => ws.close();
  }, []);
  
  return (
    <div className="live-monitor">
      <h1>Live Campaign Monitor</h1>
      
      {campaigns.map(campaign => (
        <div key={campaign.id} className="campaign-monitor">
          <div className="campaign-header">
            <h3>{campaign.name}</h3>
            <StatusBadge status={campaign.status} />
          </div>
          
          <ProgressBar 
            current={campaign.processed_records}
            total={campaign.total_records}
            showETA
          />
          
          <div className="campaign-stats">
            <Stat label="Successful" value={campaign.successful_updates} />
            <Stat label="Failed" value={campaign.failed_updates} />
            <Stat label="Speed" value={`${campaign.speed} rec/min`} />
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 4. Quality Dashboard

```tsx
// QualityDashboard.tsx
export function QualityDashboard() {
  const { data: quality } = useQualityMetrics();
  
  return (
    <div className="quality-dashboard">
      {/* Completeness Distribution */}
      <div className="distribution-chart">
        <h2>Completeness Distribution</h2>
        <BarChart 
          data={quality.distribution}
          xAxis="Completeness Range"
          yAxis="Record Count"
        />
      </div>
      
      {/* By Record Type */}
      <div className="by-type">
        <h2>Average Completeness by Type</h2>
        <div className="type-cards">
          {Object.entries(quality.byType).map(([type, score]) => (
            <TypeCard 
              key={type}
              type={type}
              score={score}
              trend={quality.trends[type]}
            />
          ))}
        </div>
      </div>
      
      {/* Top Incomplete Records */}
      <div className="incomplete-records">
        <h2>Top Candidates for Backfill</h2>
        <RecordTable 
          records={quality.topIncomplete}
          columns={['title', 'type', 'completeness', 'missing']}
          onBackfill={(record) => createCampaignForRecord(record)}
        />
      </div>
      
      {/* Missing Fields Analysis */}
      <div className="missing-fields">
        <h2>Most Common Missing Fields</h2>
        <HorizontalBarChart 
          data={quality.missingFields}
          label="field"
          value="count"
        />
      </div>
    </div>
  );
}
```

### 5. Analytics Dashboard

```tsx
// AnalyticsDashboard.tsx
export function AnalyticsDashboard() {
  const [dateRange, setDateRange] = useState({ start: '30d', end: 'now' });
  const { data: analytics } = useAnalytics(dateRange);
  
  return (
    <div className="analytics-dashboard">
      <div className="controls">
        <DateRangePicker 
          value={dateRange}
          onChange={setDateRange}
        />
      </div>
      
      {/* Completeness Trend */}
      <div className="trend-section">
        <h2>Completeness Trend</h2>
        <LineChart 
          data={analytics.trends}
          lines={[
            { key: 'avgCompleteness', label: 'Avg Completeness', color: 'blue' },
            { key: 'targetCompleteness', label: 'Target', color: 'green' }
          ]}
        />
      </div>
      
      {/* Campaign Activity */}
      <div className="activity-section">
        <h2>Campaign Activity</h2>
        <BarChart 
          data={analytics.activity}
          bars={[
            { key: 'campaignsRun', label: 'Campaigns Run' },
            { key: 'recordsProcessed', label: 'Records Processed' }
          ]}
        />
      </div>
      
      {/* Performance Metrics */}
      <div className="performance-section">
        <h2>Performance by Strategy</h2>
        <Table 
          data={analytics.performanceByStrategy}
          columns={[
            { key: 'strategy', label: 'Strategy' },
            { key: 'avgImprovement', label: 'Avg Improvement' },
            { key: 'successRate', label: 'Success Rate' },
            { key: 'avgDuration', label: 'Avg Duration' }
          ]}
        />
      </div>
      
      {/* Impact Summary */}
      <div className="impact-section">
        <h2>Overall Impact</h2>
        <div className="impact-grid">
          <ImpactCard 
            icon="📈"
            label="Records Enriched"
            value={analytics.impact.totalRecords}
          />
          <ImpactCard 
            icon="✨"
            label="Fields Filled"
            value={analytics.impact.totalFields}
          />
          <ImpactCard 
            icon="🎯"
            label="Avg Quality Gain"
            value={`+${analytics.impact.avgGain}%`}
          />
        </div>
      </div>
    </div>
  );
}
```

---

## WebSocket Integration

### Backend WebSocket Handler

```python
# app/api/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set

class BackfillWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, campaign_id: str):
        await websocket.accept()
        if campaign_id not in self.active_connections:
            self.active_connections[campaign_id] = set()
        self.active_connections[campaign_id].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, campaign_id: str):
        self.active_connections[campaign_id].remove(websocket)
    
    async def broadcast(self, campaign_id: str, message: dict):
        if campaign_id in self.active_connections:
            for connection in self.active_connections[campaign_id]:
                await connection.send_json(message)

manager = BackfillWebSocketManager()

@app.websocket("/ws/backfill/campaigns/{campaign_id}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: str):
    await manager.connect(websocket, campaign_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, campaign_id)
```

### Frontend WebSocket Hook

```typescript
// hooks/useBackfillWebSocket.ts

export function useBackfillWebSocket(campaignId: string) {
  const [updates, setUpdates] = useState<JobUpdate[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8765/ws/backfill/campaigns/${campaignId}`
    );
    
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setUpdates(prev => [...prev, update]);
    };
    
    return () => ws.close();
  }, [campaignId]);
  
  return { updates, isConnected };
}
```

---

## Routing

```typescript
// App.tsx
<Routes>
  <Route path="/backfill" element={<BackfillDashboard />} />
  <Route path="/backfill/campaigns" element={<CampaignList />} />
  <Route path="/backfill/campaigns/new" element={<CampaignWizard />} />
  <Route path="/backfill/campaigns/:id" element={<CampaignDetail />} />
  <Route path="/backfill/quality" element={<QualityDashboard />} />
  <Route path="/backfill/monitor" element={<LiveMonitor />} />
  <Route path="/backfill/analytics" element={<AnalyticsDashboard />} />
  <Route path="/backfill/schedules" element={<ScheduleManager />} />
  <Route path="/backfill/settings" element={<BackfillSettings />} />
</Routes>
```

---

## Integration Steps

### 1. Add Routes to Navigation

```tsx
// frontend/src/components/Navigation.tsx
const navItems = [
  // ... existing items
  {
    label: 'Backfill',
    path: '/backfill',
    icon: <RefreshIcon />,
    children: [
      { label: 'Dashboard', path: '/backfill' },
      { label: 'Campaigns', path: '/backfill/campaigns' },
      { label: 'Quality', path: '/backfill/quality' },
      { label: 'Monitor', path: '/backfill/monitor' },
      { label: 'Analytics', path: '/backfill/analytics' },
      { label: 'Schedules', path: '/backfill/schedules' },
    ]
  }
];
```

### 2. Add API Client

Create `frontend/src/api/backfill.ts` with all API methods

### 3. Create Components

Build React components in `frontend/src/components/backfill/`

### 4. Add WebSocket Support

Implement WebSocket handler and React hooks

### 5. Add Charts Library

```bash
npm install recharts
# or
npm install chart.js react-chartjs-2
```

### 6. Styling

Create `frontend/src/styles/backfill.css` with component styles

---

## Example Screens

### Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Backfill Dashboard                                         │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │   Total    │ │  Success   │ │    Avg     │ │ Records  │ │
│  │ Campaigns  │ │    Rate    │ │Improvement │ │Enriched  │ │
│  │     45     │ │    94%     │ │   +28%     │ │  2,500   │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                              │
│  Active Campaigns                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Artist Bio Enrichment                     [Running]   │  │
│  │ ████████████████░░░░░░░ 32/50 (64%)                  │  │
│  │ Success: 29 | Failed: 3 | Speed: 12 rec/min          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Completeness Trend                                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 100% ┤                                          ╱─    │  │
│  │  80% ┤                                    ╱─╱─╱       │  │
│  │  60% ┤                          ╱─╱─╱─╱─╱             │  │
│  │  40% ┤                ╱─╱─╱─╱─╱                       │  │
│  │  20% ┤      ╱─╱─╱─╱─╱                                 │  │
│  │   0% └────────────────────────────────────────────    │  │
│  │      Jan  Feb  Mar  Apr  May  Jun                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Create Campaign]  [View Quality Report]  [View Analytics] │
└─────────────────────────────────────────────────────────────┘
```

### Campaign Detail

```
┌─────────────────────────────────────────────────────────────┐
│  Campaign: Artist Bio Enrichment                 [Completed]│
├─────────────────────────────────────────────────────────────┤
│  ID: abc-123-def-456                                        │
│  Strategy: Selective (completeness 0-70%)                   │
│  Created: 2026-04-15 10:30 AM                               │
│  Completed: 2026-04-15 11:45 AM (1h 15m)                    │
│                                                              │
│  Progress                                                   │
│  ████████████████████████████████████ 50/50 (100%)         │
│                                                              │
│  Statistics                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐             │
│  │ Successful │ │   Failed   │ │    Avg     │             │
│  │     47     │ │     3      │ │Improvement │             │
│  │    94%     │ │     6%     │ │   +32%     │             │
│  └────────────┘ └────────────┘ └────────────┘             │
│                                                              │
│  Top Improvements                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Jane Smith      45% → 82%  (+37%)  ✨                │  │
│  │ John Doe        60% → 88%  (+28%)  ✨                │  │
│  │ Mary Johnson    52% → 79%  (+27%)  ✨                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Failed Jobs (3)                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Bob Wilson     Crawl timeout (404)         [Retry]   │  │
│  │ Alice Brown    Parse error                 [Retry]   │  │
│  │ Tom Davis      No data found                [Skip]   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Download Report]  [Create Similar]  [Delete]              │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

Phase 4 is complete when:

- [ ] Dashboard displays overall statistics
- [ ] Can create campaigns via wizard
- [ ] Campaign list shows all campaigns with filters
- [ ] Campaign detail shows job-level breakdown
- [ ] Live monitor updates in real-time via WebSocket
- [ ] Quality dashboard shows completeness distribution
- [ ] Analytics dashboard shows trends and performance
- [ ] Schedule manager allows CRUD operations
- [ ] All UI components are responsive
- [ ] No console errors

---

## Next Steps

After Phase 4:

✅ Full-featured backfill system operational
✅ Complete UI for all operations
✅ Real-time monitoring and analytics
→ **Production deployment and optimization**

---

Phase 4 completes the backfill system with a professional, user-friendly interface! 🎨
