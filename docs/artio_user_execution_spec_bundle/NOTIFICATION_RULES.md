# NOTIFICATION_RULES

## Principles
- Useful, sparse, controllable
- Prioritize explicit intent over algorithmic nudges
- Respect quiet hours and opt-outs

## Notification types

### 1. Event reminders
Trigger:
- User explicitly sets reminder
Defaults:
- Offer 2h before and 24h before
Channels:
- push preferred, in-app always if enabled

### 2. Followed creator / venue updates
Trigger:
- New published event or gallery from followed entity
Frequency:
- batched or immediate based on user preference and volume

### 3. Nearby recommendation
Trigger:
- High-confidence nearby event in next 48h
Constraint:
- only if user opted in and has location set

### 4. Trending recommendation
Trigger:
- strong regional trend matching interests
Constraint:
- maximum 2 per week initially

## Quiet hours
Default:
- 22:00 to 08:00 local time unless user chooses otherwise
Rule:
- Non-urgent recommendations suppressed until quiet hours end
- Explicit event reminders may still send if chosen reminder time falls there only if user allows overnight delivery; otherwise move to quiet-hour end and mark adjusted

## Frequency caps
- Event reminders: uncapped, user-initiated
- Follow updates: max 1 per creator per 24h unless batched digest exists
- Nearby/trending recommendations: max 3 total per week in phase 1

## Deep links
- Event reminder -> event detail
- New gallery from followed creator -> gallery detail
- New event from followed venue -> event detail
- Trending suggestion -> event detail or gallery detail

## Required settings UI
- Master notification toggle
- Event reminder channels
- Followed creator updates toggle
- Nearby recommendations toggle
- Quiet hours picker
