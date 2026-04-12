# UI.md — Artio Miner: Admin UI Specification

## Tech Stack
- React 18 + TypeScript (strict)
- Vite as build tool
- React Router v6 for routing
- TanStack Query v5 for server state
- shadcn/ui for components
- lucide-react for icons
- axios for HTTP (wrapped in `src/lib/api.ts`)
- tailwindcss

## Layout

All pages share a sidebar layout:

```
┌──────────────────────────────────────────────────────────┐
│  🎨 Artio Miner          [version]                       │
├──────────┬───────────────────────────────────────────────┤
│          │                                               │
│ Sidebar  │  Main Content Area                            │
│          │                                               │
│ Dashboard│                                               │
│ Sources  │                                               │
│ Records  │                                               │
│ Images   │                                               │
│ Export   │                                               │
│          │                                               │
└──────────┴───────────────────────────────────────────────┘
```

Sidebar nav items with icons:
- **Dashboard** (LayoutDashboard) → `/`
- **Sources** (Globe) → `/sources`
- **Records** (Database) → `/records`
- **Images** (Image) → `/images`
- **Export** (Upload) → `/export`

---

## Page: Dashboard (`/`)

Shows global stats and recent activity.

### Stats row (4 cards)
- Total Sources (number)
- Total Records (number with breakdown: pending / approved / exported)
- Pages Crawled (total number)
- Export Ready (approved but not exported count) — highlighted in green

### Active jobs panel
Shows any currently running crawl/extract jobs with progress bar and cancel button.

### Recent sources table
Last 5 sources with: name, status badge, record count, last crawled time, quick action button.

### Records by type chart
Bar chart: events / exhibitions / artists / venues / artworks — count of each.

### Confidence distribution
Donut chart: HIGH / MEDIUM / LOW record counts.

---

## Page: Sources (`/sources`)

List of all websites being mined.

### Header
- Title: "Sources"
- Button: "Add Source" (opens AddSourceDialog)

### AddSourceDialog
Modal dialog with:
- URL input (required, validated as URL)
- Name input (optional)
- Submit button: "Add & Start Mining"
- On submit: `POST /api/sources` then immediately `POST /api/mine/{id}/start`
- Shows loading state while mapping starts

### Sources table
Columns: Name/URL | Status | Pages | Records | Confidence | Last Run | Actions

**Status badges:**
- `pending` → grey
- `mapping` → blue (animated pulse)
- `crawling` → blue (animated pulse) with page count progress
- `extracting` → purple (animated pulse)
- `done` → green
- `error` → red
- `paused` → yellow

**Actions per row:**
- View (→ `/sources/{id}`)
- Run/Resume (play icon) — if status is pending/paused/done
- Pause (pause icon) — if running
- Delete (trash icon) — confirm dialog

### Source detail page (`/sources/{source_id}`)

Tabbed layout:
- **Overview** tab
- **Pages** tab
- **Records** tab
- **Jobs** tab

#### Overview tab
- Source URL, name, status, created date
- Site map viewer: collapsible tree of detected sections with content types and confidence
- Stats: pages crawled, records extracted, by type breakdown
- Action buttons: Start Mining | Map Only | Extract Only | Pause | Delete

#### Pages tab
- Filterable table: page_type filter, status filter, search
- Columns: URL | Type | Status | Depth | Method | Crawled At | Actions
- Actions: View HTML, Reclassify, Re-extract
- Page type badges: colour coded
  - artist_profile → purple
  - event_detail → blue
  - exhibition_detail → amber
  - venue_profile → green
  - unknown → grey
  - category → orange

#### Records tab
- Same as Records page but pre-filtered to this source

#### Jobs tab
- List of all jobs for this source
- Columns: Type | Status | Started | Completed | Duration | Error
- Status badges with colours

---

## Page: Records (`/records`)

Browse and review all extracted records across all sources.

### Filters bar
- Source filter (dropdown, "All sources")
- Type filter: All | Events | Exhibitions | Artists | Venues | Artworks
- Status filter: All | Pending | Approved | Rejected | Exported
- Confidence filter: All | HIGH | MEDIUM | LOW
- Text search (searches title field)
- Bulk action: "Approve all HIGH confidence" button (confirmation required)

### Records grid
Card-based layout (not table) — 3 columns on wide screen, 2 on medium, 1 on narrow.

Each card shows:
```
┌──────────────────────────────────┐
│  [primary image thumbnail]       │
│                                  │
│  EVENT                   HIGH ●  │
│  Gallery Opening Night           │
│  Venue Name · 15 Apr 2026        │
│                                  │
│  [Approve] [Reject] [Edit]       │
└──────────────────────────────────┘
```

- Record type badge (top left, colour coded)
- Confidence band badge (top right: HIGH=green, MEDIUM=amber, LOW=red)
- Title (large, truncated at 2 lines)
- Subtitle: venue + date for events, nationality for artists, city for venues
- 3 action buttons: Approve (green), Reject (red outline), Edit (opens detail)

### Record detail page (`/records/{record_id}`)

Split layout: left panel (fields) | right panel (images)

#### Left panel — Record fields

All fields shown with current value. Edit button at top toggles edit mode.

**Edit mode:**
- All text fields become inputs/textareas
- Array fields (mediums, collections, artist_names) become tag inputs
  - Each tag shown as a chip with × to remove
  - Text input at end to add new tag
- Date fields become date pickers
- Save / Cancel buttons

**Fields shown by record type:**

Events & Exhibitions:
- Title (text)
- Description (textarea)
- Start Date (date)
- End Date (date)
- Venue Name (text)
- Venue Address (text)
- Artists (tag input)
- Ticket URL (text)
- Is Free (toggle)
- Price Text (text)
- Source URL (link)

Artists:
- Name (text)
- Bio (textarea)
- Nationality (text)
- Birth Year (number)
- Mediums (tag input)
- Collections (tag input)
- Website URL (text)
- Instagram URL (text)
- Email (text)
- Source URL (link)

Venues:
- Name (text)
- Description (textarea)
- Address (text)
- City (text)
- Country (text)
- Website URL (text)
- Phone (text)
- Email (text)
- Opening Hours (textarea)
- Source URL (link)

Artworks:
- Title (text)
- Artist Name (text)
- Medium (text)
- Year (number)
- Dimensions (text)
- Description (textarea)
- Price (text)
- Source URL (link)

Below fields: confidence score bar, confidence reasons list, admin notes textarea.

#### Right panel — Images

Header: "Images ({count})" with type filter tabs: All | Profile | Artwork | Poster | Venue

Image grid (2 columns):
```
┌────────┐ ┌────────┐
│        │ │        │
│  img   │ │  img   │
│        │ │        │
└────────┘ └────────┘
  profile    artwork
  85%        72%
  [★ Set]    [★ Set]
```

Each image:
- Thumbnail (square, object-cover)
- Type label and confidence percentage
- "Set as primary" button (star icon) — highlights if currently primary
- Click thumbnail → opens full-size in lightbox

Primary image highlighted with coloured border.

Actions (bottom of panel):
- Approve button (large, green)
- Reject button (outline, red)
- Link to source page

---

## Page: Images (`/images`)

Browse all collected images across all sources.

### Filters
- Source filter
- Type filter: All | Profile | Artwork | Poster | Venue | Unknown
- Valid only toggle (default: on — only show is_valid=true)

### Image masonry grid
Responsive grid of image thumbnails.

Each image:
- Thumbnail
- Hover overlay: type badge, confidence, alt text, "View record" link

---

## Page: Export (`/export`)

Review and push approved records to Artio.

### Artio connection status
Shows ARTIO_API_URL and whether it's configured. Warning if not configured.

### Export preview
Summary cards:
- Ready to export: N records (approved, not yet exported)
- Already exported: N records total
- By type breakdown table

### Export action
- Source filter (optional — export from one source or all)
- "Push to Artio" button → calls `POST /api/export/push`
- Progress modal while pushing
- Result: "Exported 45 records. 2 failed." with error details

### Export history table
Last 50 exports: record title | type | exported at | status

---

## Shared Components

### StatusBadge
Props: `status: string`
Renders coloured badge. Map:
- done, approved, exported → green
- running, crawling, extracting, mapping → blue (pulsing)
- pending → grey
- paused → yellow
- error, rejected, failed → red

### ConfidenceBadge
Props: `band: "HIGH" | "MEDIUM" | "LOW", score: number`
HIGH → green, MEDIUM → amber, LOW → red
Shows band label + score: "HIGH · 82"

### RecordTypeBadge
Props: `type: string`
event → blue, exhibition → amber, artist → purple,
venue → green, artwork → pink, unknown → grey

### ImageThumbnail
Props: `url: string, alt: string, imageType: string`
Square image with type badge overlay. onError → placeholder.

### ConfidenceBar
Props: `score: number, reasons: string[]`
Progress bar (green/amber/red by score) with tooltip showing reasons list.

### TagInput
Props: `values: string[], onChange: (values: string[]) => void`
Renders existing values as chips with ×, plus text input to add new.

---

## API Client (`frontend/src/lib/api.ts`)

Typed axios wrapper. All functions return typed responses.
Base URL from `import.meta.env.VITE_API_URL` (default: `http://localhost:8000`).

```typescript
// Sources
export const getSources = (): Promise<PaginatedResponse<Source>>
export const getSource = (id: string): Promise<Source>
export const createSource = (data: CreateSourceInput): Promise<Source>
export const deleteSource = (id: string): Promise<void>

// Mining
export const startMining = (sourceId: string, opts?: MineOptions): Promise<Job>
export const getMiningStatus = (sourceId: string): Promise<MiningStatus>
export const mapSite = (sourceId: string): Promise<SiteMap>
export const pauseMining = (sourceId: string): Promise<void>
export const resumeMining = (sourceId: string): Promise<void>

// Pages
export const getPages = (params: PageFilters): Promise<PaginatedResponse<Page>>
export const getPage = (id: string): Promise<Page>
export const reclassifyPage = (id: string): Promise<Page>
export const reextractPage = (id: string): Promise<Record>

// Records
export const getRecords = (params: RecordFilters): Promise<PaginatedResponse<Record>>
export const getRecord = (id: string): Promise<Record>
export const updateRecord = (id: string, data: Partial<Record>): Promise<Record>
export const approveRecord = (id: string): Promise<Record>
export const rejectRecord = (id: string, reason?: string): Promise<Record>
export const bulkApprove = (params: BulkApproveParams): Promise<{ approved_count: number }>
export const setPrimaryImage = (recordId: string, imageId: string): Promise<Record>

// Images
export const getImages = (params: ImageFilters): Promise<PaginatedResponse<Image>>
export const validateImages = (urls: string[]): Promise<ValidationResult[]>

// Export
export const getExportPreview = (sourceId?: string): Promise<ExportPreview>
export const pushToArtio = (params: ExportParams): Promise<ExportResult>

// Stats
export const getStats = (): Promise<GlobalStats>
```
