# DATA_MODEL

## Entities

### CreatorAccount
Fields:
- id: string
- owner_user_id: string
- role_type: "artist" | "venue_owner"
- display_name: string
- slug: string
- avatar_url: string|null
- cover_url: string|null
- bio: string|null
- location_label: string|null
- website_url: string|null
- social_links: SocialLink[]
- status: "active" | "inactive"
- created_at: datetime
- updated_at: datetime

### SocialLink
Fields:
- label: string
- url: string

### CreatorProfileSectionConfig
Fields:
- id: string
- creator_id: string
- section_key: "hero" | "bio" | "featured" | "upcoming_events" | "recent_galleries" | "contact" | "venue_info"
- is_enabled: boolean
- order_index: number
- config_json: object

### CreatorEventDraft
Fields:
- id: string
- creator_id: string
- title: string
- status: "draft" | "scheduled" | "published" | "archived"
- scheduled_publish_at: datetime|null
- payload_json: object
- validation_state: "valid" | "invalid" | "incomplete"
- created_at: datetime
- updated_at: datetime

### CreatorGalleryDraft
Fields:
- id: string
- creator_id: string
- title: string
- status: "draft" | "scheduled" | "published" | "archived"
- scheduled_publish_at: datetime|null
- payload_json: object
- validation_state: "valid" | "invalid" | "incomplete"
- created_at: datetime
- updated_at: datetime

### Published Event / Gallery
Reuse the shared event/gallery entities from the user system, but preserve creator ownership references and publication metadata.

### MediaAsset
Fields:
- id: string
- creator_id: string
- media_type: "image" | "video"
- original_url: string
- optimized_url: string|null
- thumbnail_url: string|null
- width: number|null
- height: number|null
- alt_text: string|null
- created_at: datetime

### CreatorAnalyticsSnapshot
Fields:
- id: string
- creator_id: string
- date_bucket: date
- profile_views: number
- event_views: number
- gallery_views: number
- saves: number
- follows: number
- attend_intents: number

## Suggested indexes
- CreatorAccount.slug
- CreatorEventDraft.creator_id + status
- CreatorGalleryDraft.creator_id + status
- MediaAsset.creator_id + created_at
- CreatorAnalyticsSnapshot.creator_id + date_bucket
