# API_CONTRACTS

Base principles:
- Keep endpoints role-safe: user APIs must not leak creator draft/admin fields
- Support pagination, filtering, and stable IDs
- Return lightweight card payloads for lists and richer payloads for detail views

## Auth
### GET /me
Returns current user profile and preferences

### PATCH /me
Updates profile fields:
- home_location
- interests
- onboarding_completed

## Preferences
### GET /me/notification-preferences
### PATCH /me/notification-preferences

## Explore / discovery
### GET /explore
Query:
- lat, lng
- date_window=today|tonight|week|weekend|custom
- category[]
- price_type[]
- following_only
- page
- page_size

Response:
- rails: RecommendationRail[]
- feed_items: FeedItem[]
- facets

FeedItem union:
- event_card
- gallery_card
- creator_suggestion_card

### GET /search
Query:
- q
- type=all|event|gallery|creator|venue
- lat,lng
- page,page_size

## Events
### GET /events
Query:
- start_from
- start_to
- lat,lng,radius_km
- category[]
- price_type[]
- sort=recommended|distance|soonest|popular
- page,page_size

### GET /events/:id
Returns full event detail with:
- event
- related_events[]
- related_gallery|null
- creator_summary
- venue_summary|null

### POST /events/:id/save
### DELETE /events/:id/save

### POST /events/:id/attend-intent
Optional if no ticketing ownership exists. Stores lightweight attendance intent.

### POST /events/:id/reminders
Body:
- remind_at OR preset in ["2h_before","24h_before"]
- channel

### DELETE /events/:id/reminders/:reminderId

## Galleries
### GET /galleries
Query:
- tag[]
- creator_id
- sort=recommended|newest|popular
- lat,lng,radius_km
- page,page_size

### GET /galleries/:id
Returns:
- gallery
- items[]
- creator_summary
- related_galleries[]
- related_events[]

### POST /galleries/:id/save
### DELETE /galleries/:id/save

## Follows
### GET /me/follows
### POST /creators/:id/follow
### DELETE /creators/:id/follow

## Saved
### GET /me/saved
Query:
- type=all|event|gallery
- page,page_size

## Notifications
### GET /me/notifications
Query:
- unread_only
- page,page_size

### POST /me/notifications/:id/read
### POST /me/notifications/read-all

## Analytics ingestion
### POST /analytics/events
Body:
- event_name
- properties
- occurred_at

## Response shaping
Card payload minimums:
EventCard:
- id, title, hero_image_url, start_at, location_label, creator_name, save_state, reminder_state, badges[], ranking_reason

GalleryCard:
- id, title, cover_image_url, creator_name, save_state, badges[], ranking_reason

CreatorCard:
- id, display_name, avatar_url, type, follower_count, tags[]
