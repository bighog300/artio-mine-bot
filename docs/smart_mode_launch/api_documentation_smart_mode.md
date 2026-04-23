# Smart Mode API Documentation

Base route prefix: `/api/smart-mine`

## 1) Create Smart Mode run
`POST /api/smart-mine/`

### Request body
```json
{
  "url": "https://example.com",
  "name": "Example Source",
  "source_id": "optional-existing-source-id"
}
```

### Response
```json
{
  "source_id": "<id>",
  "status": "queued",
  "message": "Smart mining job accepted"
}
```

## 2) Get run status
`GET /api/smart-mine/{source_id}/status`

### Response fields
- `source_id`
- `status`
- `pages_count`
- `records_count`
- `updated_at`
- `job_status` (`queued|running|completed|failed`)
- `error`
- `helpful_error`

## 3) Retry failed run
`POST /api/smart-mine/{source_id}/retry`

Retry is allowed only when source status is one of:
- `failed`
- `error`
- `needs_human_review`

## 4) List templates
`GET /api/smart-mine/templates`

Returns template metadata:
- `id`
- `name`
- `usage_count`

## 5) Get template detail
`GET /api/smart-mine/templates/{template_id}`

Returns full template object.

## 6) Get Smart Mode metrics (admin only)
`GET /api/smart-mine/metrics`

Returns:
- cache statistics
- token/cost usage totals
- operation-level usage
- daily cost report
- recent cost alerts

## Errors
- `404`: source/template not found.
- `422`: retry requested for non-retryable source state.
- `403`: metrics endpoint requested by non-admin principal.
