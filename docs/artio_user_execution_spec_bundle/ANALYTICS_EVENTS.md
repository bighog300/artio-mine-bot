# ANALYTICS_EVENTS

## Naming principles
- Verb-noun
- Clear distinction between impression, click, save, setting change, and notification lifecycle

## Core events

### Discovery
- explore_viewed
- rail_viewed
- card_impression
- card_clicked
- filter_applied
- search_performed
- search_result_clicked

### Event
- event_detail_viewed
- event_saved
- event_unsaved
- event_attend_intent_created
- event_reminder_opened
- event_reminder_created
- event_reminder_deleted
- add_to_calendar_clicked
- ticket_cta_clicked

### Gallery
- gallery_detail_viewed
- gallery_saved
- gallery_unsaved
- gallery_item_viewed
- gallery_completed
- creator_follow_clicked_from_gallery

### Following / retention
- creator_followed
- creator_unfollowed
- saved_tab_viewed
- notification_inbox_viewed
- notification_opened
- notification_marked_read

### Onboarding / preferences
- onboarding_started
- onboarding_completed
- interest_selected
- location_permission_result
- notification_permission_result
- notification_preferences_updated

## Required properties examples
card_impression:
- item_id
- item_type
- rail_type
- position
- ranking_reason

event_saved:
- event_id
- source_surface
- had_reminder_already

notification_opened:
- notification_id
- notification_type
- deep_link_target

## Success metrics
- save rate
- reminder creation rate
- follow rate
- 7-day return rate
- notification open rate
- event detail CTR from explore
