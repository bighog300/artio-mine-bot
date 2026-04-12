# API.md — Artio Miner: API Specification

## Base URL
`http://localhost:8000`

## Common Response Format

All endpoints return JSON. Errors use this format:
```json
{
  "detail": "Human readable error message",
  "code": "snake_case_error_code"
}
```

Paginated lists use:
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

---

## Health

### GET /health
Returns service health status.

Response `200`:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "ok",
  "openai": "configured"
}
```

---

## Sources — `/api/sources`

### GET /api/sources
List all sources with summary stats.

Query params: `skip=0`, `limit=50`

Response `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "url": "https://art.co.za",
      "name": "Art.co.za",
      "status": "done",
      "total_pages": 342,
      "total_records": 87,
      "last_crawled_at": "2026-04-12T10:00:00Z",
      "created_at": "2026-04-12T09:00:00Z",
      "stats": {
        "pending_records": 12,
        "approved_records": 60,
        "rejected_records": 15,
        "high_confidence": 45,
        "medium_confidence": 30,
        "low_confidence": 12
      }
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 50
}
```

### POST /api/sources
Create a new source.

Request:
```json
{
  "url": "https://art.co.za",
  "name": "Art.co.za"
}
```

Response `201`:
```json
{
  "id": "uuid",
  "url": "https://art.co.za",
  "name": "Art.co.za",
  "status": "pending",
  "created_at": "2026-04-12T09:00:00Z"
}
```

Errors: `409` if URL already exists.

### GET /api/sources/{source_id}
Get a single source with full detail including site_map.

Response `200`: full Source object including `site_map` JSON.

### PATCH /api/sources/{source_id}
Update source name or status.

Request: any subset of `{ "name": string, "status": string }`

### DELETE /api/sources/{source_id}
Delete a source and all its pages, records, images, and jobs.

Response `204`.

---

## Mining — `/api/mine`

### POST /api/mine/{source_id}/start
Start the full mining pipeline for a source.
Triggers: map → crawl → extract → score in sequence.
Returns immediately with a job ID — pipeline runs in background.

Request body (optional):
```json
{
  "max_depth": 3,
  "max_pages": 500,
  "sections": ["events", "exhibitions", "artists"]
}
```

Response `202`:
```json
{
  "job_id": "uuid",
  "source_id": "uuid",
  "status": "pending",
  "message": "Mining pipeline started"
}
```

### POST /api/mine/{source_id}/map
Run only the site mapping step. Identifies sections and structure.

Response `200`:
```json
{
  "source_id": "uuid",
  "site_map": {
    "root_url": "https://art.co.za",
    "platform": "custom",
    "sections": [
      {
        "name": "Artists",
        "url": "https://art.co.za/artists/",
        "content_type": "artist_directory",
        "pagination_type": "letter",
        "index_pattern": "https://art.co.za/artists/[letter]",
        "confidence": 90
      },
      {
        "name": "Exhibitions",
        "url": "https://art.co.za/exhibitions/",
        "content_type": "exhibition_listing",
        "pagination_type": "numbered",
        "confidence": 80
      }
    ]
  }
}
```

### POST /api/mine/{source_id}/crawl
Run the crawl step only (requires site map to exist).

Response `202`: `{ "job_id": "uuid", "status": "pending" }`

### POST /api/mine/{source_id}/extract
Run extraction on all fetched-but-not-extracted pages.

Response `202`: `{ "job_id": "uuid", "status": "pending" }`

### POST /api/mine/{source_id}/pause
Pause any running crawl jobs.

### POST /api/mine/{source_id}/resume
Resume a paused crawl.

### GET /api/mine/{source_id}/status
Get current pipeline status and progress.

Response `200`:
```json
{
  "source_id": "uuid",
  "status": "crawling",
  "current_job": {
    "id": "uuid",
    "job_type": "crawl_section",
    "status": "running",
    "started_at": "2026-04-12T09:30:00Z"
  },
  "progress": {
    "pages_crawled": 150,
    "pages_total_estimated": 342,
    "records_extracted": 45,
    "percent_complete": 44
  }
}
```

---

## Pages — `/api/pages`

### GET /api/pages
List pages, optionally filtered.

Query params: `source_id`, `status`, `page_type`, `skip=0`, `limit=50`

Response `200`: paginated list of Page objects.

```json
{
  "items": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "url": "https://art.co.za/ericduplan/",
      "page_type": "artist_profile",
      "status": "extracted",
      "title": "Eric Duplan | Art.co.za",
      "depth": 2,
      "fetch_method": "httpx",
      "crawled_at": "2026-04-12T09:30:00Z",
      "record_count": 1
    }
  ],
  "total": 342,
  "skip": 0,
  "limit": 50
}
```

### GET /api/pages/{page_id}
Get full page detail including stored HTML.

### POST /api/pages/{page_id}/reclassify
Re-run AI classification on a page.

### POST /api/pages/{page_id}/reextract
Re-run extraction on a page (creates new Record or updates existing).

---

## Records — `/api/records`

### GET /api/records
List records with filters.

Query params: `source_id`, `record_type`, `status`, `confidence_band`,
`search` (text search on title), `skip=0`, `limit=50`

Response `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "record_type": "artist",
      "status": "pending",
      "title": "Eric Duplan",
      "description": "Eric Duplan is a full time abstract artist...",
      "confidence_score": 82,
      "confidence_band": "HIGH",
      "confidence_reasons": ["name present", "bio present", "avatar image found"],
      "source_url": "https://art.co.za/ericduplan/",
      "image_count": 5,
      "primary_image_url": "https://art.co.za/images/ericduplan.jpg",
      "created_at": "2026-04-12T09:45:00Z"
    }
  ],
  "total": 87,
  "skip": 0,
  "limit": 50
}
```

### GET /api/records/{record_id}
Get full record detail with all fields and associated images.

Response `200`:
```json
{
  "id": "uuid",
  "record_type": "artist",
  "status": "pending",
  "title": "Eric Duplan",
  "bio": "Full bio text...",
  "nationality": "South African",
  "birth_year": 1962,
  "mediums": ["oil painting"],
  "collections": ["UNISA", "Old Mutual"],
  "website_url": "https://www.ericduplan.com",
  "instagram_url": null,
  "avatar_url": "https://art.co.za/images/ericduplan.jpg",
  "confidence_score": 82,
  "confidence_band": "HIGH",
  "confidence_reasons": ["name present", "bio present", "avatar image found"],
  "images": [
    {
      "id": "uuid",
      "url": "https://...",
      "image_type": "profile",
      "alt_text": "Eric Duplan portrait",
      "confidence": 85,
      "is_valid": true
    }
  ],
  "primary_image_id": "uuid",
  "source_url": "https://art.co.za/ericduplan/",
  "created_at": "2026-04-12T09:45:00Z"
}
```

### PATCH /api/records/{record_id}
Update any field on a record. Only allowed when status is `pending`.

Request: any subset of record fields.

Response `200`: updated Record object.

### POST /api/records/{record_id}/approve
Approve a record for export.

Response `200`: `{ "id": "uuid", "status": "approved" }`

### POST /api/records/{record_id}/reject
Reject a record.

Request: `{ "reason": "string (optional)" }`

Response `200`: `{ "id": "uuid", "status": "rejected" }`

### POST /api/records/bulk-approve
Bulk approve records matching criteria.

Request:
```json
{
  "source_id": "uuid",
  "min_confidence": 70,
  "record_type": "artist"
}
```

Response `200`: `{ "approved_count": 45 }`

### POST /api/records/{record_id}/set-primary-image
Set the primary image for a record.

Request: `{ "image_id": "uuid" }`

Response `200`: updated Record.

---

## Images — `/api/images`

### GET /api/images
List images with filters.

Query params: `record_id`, `source_id`, `image_type`, `is_valid`, `skip=0`, `limit=50`

Response `200`: paginated list of Image objects.

### POST /api/images/validate
Validate a list of image URLs (HEAD requests).

Request: `{ "urls": ["https://...", "https://..."] }`

Response `200`:
```json
{
  "results": [
    { "url": "https://...", "is_valid": true, "mime_type": "image/jpeg", "status_code": 200 },
    { "url": "https://...", "is_valid": false, "error": "404 Not Found" }
  ]
}
```

---

## Export — `/api/export`

### GET /api/export/preview
Preview what would be exported (approved, not yet exported records).

Query params: `source_id` (optional)

Response `200`:
```json
{
  "record_count": 45,
  "by_type": {
    "artist": 20,
    "event": 15,
    "exhibition": 8,
    "venue": 2
  },
  "artio_configured": true
}
```

### POST /api/export/push
Push approved records to Artio API.

Request:
```json
{
  "source_id": "uuid",
  "record_ids": ["uuid", "uuid"]
}
```

If `record_ids` is empty, exports all approved non-exported records for the source.

Response `200`:
```json
{
  "exported_count": 45,
  "failed_count": 2,
  "errors": ["Record uuid: 422 Unprocessable Entity"]
}
```

### GET /api/export/history
List previously exported records with timestamps.

---

## Stats — `/api/stats`

### GET /api/stats
Global dashboard stats.

Response `200`:
```json
{
  "sources": {
    "total": 5,
    "active": 2,
    "done": 3
  },
  "records": {
    "total": 420,
    "pending": 80,
    "approved": 300,
    "rejected": 40,
    "exported": 260,
    "by_type": {
      "artist": 150,
      "event": 120,
      "exhibition": 80,
      "venue": 40,
      "artwork": 30
    },
    "by_confidence": {
      "HIGH": 200,
      "MEDIUM": 140,
      "LOW": 80
    }
  },
  "pages": {
    "total": 1240,
    "crawled": 1200,
    "error": 40
  }
}
```
