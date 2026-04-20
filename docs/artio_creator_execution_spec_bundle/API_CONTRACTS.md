# API_CONTRACTS

## Creator account
### GET /creator/me
### PATCH /creator/me

## Dashboard
### GET /creator/dashboard
Returns:
- summary cards
- draft counts
- upcoming events
- recent galleries
- profile completeness

## Content lists
### GET /creator/content
Query:
- type=event|gallery|all
- status=draft|scheduled|published|archived|all
- page,page_size

## Event creation/editing
### POST /creator/events/drafts
Creates draft

### GET /creator/events/drafts/:id
### PATCH /creator/events/drafts/:id
Updates draft payload

### POST /creator/events/drafts/:id/validate
Returns field-level validation result

### POST /creator/events/drafts/:id/preview
Returns user-facing event preview payload

### POST /creator/events/drafts/:id/publish
Body:
- publish_mode: "now" | "schedule"
- scheduled_publish_at?: datetime

### POST /creator/events/:id/archive
### DELETE /creator/events/:id

## Gallery creation/editing
### POST /creator/galleries/drafts
### GET /creator/galleries/drafts/:id
### PATCH /creator/galleries/drafts/:id
### POST /creator/galleries/drafts/:id/validate
### POST /creator/galleries/drafts/:id/preview
### POST /creator/galleries/drafts/:id/publish
Body:
- publish_mode: "now" | "schedule"
- scheduled_publish_at?: datetime

### POST /creator/galleries/:id/archive
### DELETE /creator/galleries/:id

## Media
### POST /creator/media
Upload one or multiple assets
Response includes asset IDs and optimized versions if available

### DELETE /creator/media/:id
Only if not in use or with replacement handling

## Public page configuration
### GET /creator/public-page
### PATCH /creator/public-page
Fields:
- section order
- enabled sections
- featured content references
- contact/link config
- venue details

## Analytics
### GET /creator/analytics
Query:
- range=7d|30d|90d|custom

Response:
- summary metrics
- top events
- top galleries
- timeline buckets

## Safety / constraints
- Creator APIs only expose creator-owned resources
- Published payloads must align with user-facing card/detail models
