# DATA_MODEL

## Entities

### User
Fields:
- id: string
- name: string
- email: string
- avatar_url: string|null
- home_location: { lat: number, lng: number, label: string }|null
- onboarding_completed: boolean
- interests: string[]
- notification_preferences: NotificationPreference
- created_at: datetime
- updated_at: datetime

### NotificationPreference
Fields:
- reminders_enabled: boolean
- followed_creator_updates_enabled: boolean
- nearby_recommendations_enabled: boolean
- quiet_hours_start: string|null
- quiet_hours_end: string|null
- push_enabled: boolean
- email_enabled: boolean
- in_app_enabled: boolean

### Creator
Fields:
- id: string
- type: "artist" | "venue" | "collective"
- display_name: string
- avatar_url: string|null
- cover_url: string|null
- bio: string|null
- location_label: string|null
- is_verified: boolean
- follower_count: number
- tags: string[]
- created_at: datetime
- updated_at: datetime

### Venue
Fields:
- id: string
- creator_id: string
- location: { lat: number, lng: number, address: string, city: string }
- accessibility_notes: string|null
- capacity: number|null

### Event
Fields:
- id: string
- title: string
- slug: string
- status: "published" | "cancelled" | "ended"
- start_at: datetime
- end_at: datetime|null
- timezone: string
- location: { lat: number, lng: number, address: string, city: string, venue_name: string|null }
- creator_id: string
- venue_creator_id: string|null
- hero_image_url: string|null
- price_type: "free" | "paid" | "donation" | "unknown"
- ticket_url: string|null
- categories: string[]
- tags: string[]
- description: string
- saved_count: number
- attend_count: number
- view_count: number
- gallery_id: string|null
- created_at: datetime
- updated_at: datetime

### Gallery
Fields:
- id: string
- title: string
- slug: string
- creator_id: string
- cover_image_url: string|null
- description: string|null
- tags: string[]
- categories: string[]
- location_label: string|null
- saved_count: number
- view_count: number
- created_at: datetime
- updated_at: datetime

### GalleryItem
Fields:
- id: string
- gallery_id: string
- media_type: "image" | "video"
- media_url: string
- thumbnail_url: string|null
- caption: string|null
- commentary: string|null
- order_index: number

### Save
Fields:
- id: string
- user_id: string
- entity_type: "event" | "gallery"
- entity_id: string
- created_at: datetime

### Follow
Fields:
- id: string
- user_id: string
- creator_id: string
- created_at: datetime

### Reminder
Fields:
- id: string
- user_id: string
- event_id: string
- remind_at: datetime
- channel: "push" | "email" | "in_app"
- status: "scheduled" | "sent" | "cancelled" | "failed"
- created_at: datetime

### Notification
Fields:
- id: string
- user_id: string
- type: "event_reminder" | "followed_creator_update" | "nearby_recommendation" | "trending_recommendation"
- title: string
- body: string
- deep_link: string
- is_read: boolean
- sent_at: datetime|null
- created_at: datetime

## Suggested indexes
- Event: start_at, status, location.city, creator_id, tags
- Gallery: creator_id, created_at, tags
- Save: user_id + entity_type, entity_id
- Follow: user_id + creator_id
- Reminder: user_id + event_id, remind_at + status
- Notification: user_id + created_at, user_id + is_read
