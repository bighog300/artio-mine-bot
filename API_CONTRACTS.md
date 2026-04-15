# AI Source Mapper — API Contracts

## 1. Conventions

- All routes use `/api`
- All list responses return `{ items, total, skip, limit }` where relevant
- Preview APIs return ephemeral data only
- Draft mutations should return the updated object

## 2. Suggested schemas

### 2.1 Mapping draft summary

```json
{
  "id": "map_draft_123",
  "source_id": "src_123",
  "version_number": 3,
  "status": "draft",
  "scan_status": "completed",
  "page_type_count": 4,
  "mapping_count": 27,
  "approved_count": 18,
  "needs_review_count": 6,
  "created_at": "2026-04-15T10:00:00Z",
  "updated_at": "2026-04-15T10:20:00Z",
  "published_at": null,
  "published_by": null
}
```

### 2.2 Mapping row

```json
{
  "id": "map_row_123",
  "draft_id": "map_draft_123",
  "page_type_key": "event_detail",
  "selector": ".event-date",
  "extraction_mode": "text",
  "sample_value": "Fri 12 Sept 2026",
  "destination_entity": "event",
  "destination_field": "start_date",
  "category_target": "live-events",
  "confidence_score": 0.91,
  "status": "proposed",
  "rationale": ["Repeated across 8 event pages", "Date-like text pattern"],
  "transforms": ["date_parse"],
  "is_required": false,
  "is_enabled": true,
  "sort_order": 10
}
```

### 2.3 Preview result

```json
{
  "sample_page_id": "sample_123",
  "page_url": "https://example.com/events/foo",
  "page_type_key": "event_detail",
  "extractions": [
    {
      "mapping_row_id": "map_row_123",
      "source_selector": ".event-date",
      "raw_value": "Fri 12 Sept 2026",
      "normalized_value": "2026-09-12",
      "destination_entity": "event",
      "destination_field": "start_date",
      "category_target": "live-events",
      "confidence_score": 0.91,
      "warning": null
    }
  ],
  "record_preview": {
    "record_type": "event",
    "title": "Sample Event",
    "start_date": "2026-09-12",
    "venue_name": "Main Hall"
  }
}
```

## 3. Proposed endpoints

### 3.1 Create source mapping draft

`POST /api/sources/{source_id}/mapping-drafts`

Request:

```json
{
  "scan_mode": "standard",
  "allowed_paths": ["/events", "/artists"],
  "blocked_paths": ["/privacy", "/terms"],
  "max_pages": 50,
  "max_depth": 3,
  "sample_pages_per_type": 5
}
```

Response:
- `201 Created`
- returns draft summary

### 3.2 Start or restart scan

`POST /api/sources/{source_id}/mapping-drafts/{draft_id}/scan`

Response:

```json
{
  "draft_id": "map_draft_123",
  "scan_status": "queued",
  "job_id": "job_123",
  "message": "Mapping scan queued."
}
```

### 3.3 Get scan status

`GET /api/sources/{source_id}/mapping-drafts/{draft_id}`

Response includes:
- draft summary
- page type summaries
- scan warnings
- status counts

### 3.4 List page types

`GET /api/sources/{source_id}/mapping-drafts/{draft_id}/page-types`

Response:

```json
{
  "items": [
    {
      "key": "event_detail",
      "label": "Event Detail",
      "sample_count": 12,
      "confidence_score": 0.88,
      "sample_urls": ["https://example.com/events/a"],
      "field_candidate_count": 9
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### 3.5 List mapping rows

`GET /api/sources/{source_id}/mapping-drafts/{draft_id}/rows`

Query params:
- `page_type_key`
- `status`
- `destination_entity`
- `min_confidence`
- `skip`
- `limit`

### 3.6 Update mapping row

`PATCH /api/sources/{source_id}/mapping-drafts/{draft_id}/rows/{row_id}`

Request example:

```json
{
  "destination_entity": "event",
  "destination_field": "venue_name",
  "category_target": null,
  "status": "approved",
  "is_enabled": true,
  "sort_order": 20,
  "transforms": ["trim"]
}
```

### 3.7 Bulk update mapping rows

`POST /api/sources/{source_id}/mapping-drafts/{draft_id}/rows/bulk`

Request example:

```json
{
  "row_ids": ["map_row_1", "map_row_2"],
  "action": "approve"
}
```

Supported actions:
- approve
- reject
- ignore
- disable
- enable
- move_destination

### 3.8 Preview a sample page

`POST /api/sources/{source_id}/mapping-drafts/{draft_id}/preview`

Request:

```json
{
  "sample_page_id": "sample_123"
}
```

Response:
- preview result object

### 3.9 Run sample extraction review

`POST /api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run`

Request:

```json
{
  "page_type_keys": ["event_detail", "artist_detail"],
  "sample_count": 10
}
```

Response:

```json
{
  "sample_run_id": "sample_run_123",
  "status": "queued"
}
```

### 3.10 List sample run results

`GET /api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run/{sample_run_id}`

Returns generated sample previews and review status.

### 3.11 Publish draft

`POST /api/sources/{source_id}/mapping-drafts/{draft_id}/publish`

Response:

```json
{
  "draft_id": "map_draft_123",
  "status": "published",
  "published_at": "2026-04-15T11:00:00Z",
  "source_id": "src_123",
  "active_mapping_version_id": "map_draft_123"
}
```

### 3.12 List mapping version history

`GET /api/sources/{source_id}/mapping-versions`

### 3.13 Roll back to a version

`POST /api/sources/{source_id}/mapping-versions/{version_id}/rollback`

Response returns the newly created draft or active published version depending on chosen implementation.

## 4. Error behavior

- Scan endpoints should return `202`/queued states for async work.
- Missing source or draft returns `404`.
- Invalid status transition returns `409`.
- Preview should return partial results with warnings instead of failing the entire response where possible.
