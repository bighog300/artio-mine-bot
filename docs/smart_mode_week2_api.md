# Smart Mode Week 2 API

Implemented Smart Mode API with background task execution, template library integration, and cache support.

## Endpoints

- `POST /api/smart-mine/`
- `GET /api/smart-mine/{id}/status`
- `POST /api/smart-mine/{id}/retry`
- `GET /api/smart-mine/templates`
- `GET /api/smart-mine/templates/{id}`

## Template System

- JSON-backed template library at `app/ai/template_data/`
- Weighted similarity matching with threshold `0.75`
- Placeholder substitution for `{url}` and `{domain}`

## Caching

- Analysis caching TTL: 24h
- Template match caching TTL: 1h
- Async decorator for reuse in SmartMiner
