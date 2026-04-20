# SCREEN_MAP

## Navigation model
Primary bottom navigation:
1. Explore
2. Events
3. Galleries
4. Saved
5. Profile

Secondary overlays / views:
- Notification inbox
- Filter modal / sheet
- Search
- Event reminder picker
- Share sheet
- Report content modal

## Screen inventory

### 1. Onboarding
Purpose:
- Set expectations and collect preference signals for cold-start recommendations

Required UI:
- Welcome value proposition
- Role choice hidden from this bundle; this bundle defaults to explorer/user
- Interest selection: categories, styles, venue types, neighborhoods/cities
- Location permission prompt
- Notification permission prompt
- Optional “Follow starter creators/venues” step

States:
- First-time user
- Returning user without completed onboarding

### 2. Explore feed
Purpose:
- Mixed feed of recommended events and galleries

Modules:
- Search entry
- Quick filters row: Tonight, This week, Nearby, Free, Trending
- Personalized recommendation rail
- Mixed feed stream
- Following rail
- New near you rail
- Empty state for low inventory

Card types:
- Event card
- Gallery card
- Creator/venue suggestion card

### 3. Events listing
Purpose:
- Dedicated event browsing

Required UI:
- Date segmented controls: Today, Tonight, This week, Weekend, Custom
- Location chip
- Category filters
- Map/list toggle only if map exists already in codebase
- Sort: Recommended, Distance, Soonest, Popular

### 4. Event detail
Purpose:
- Support commitment and reminder intent

Required UI hierarchy:
1. Hero image/poster
2. Title
3. Date/time
4. Venue and location
5. Primary CTA row: Save, Attend/Get tickets, Reminder
6. Description
7. Host/artist/venue section
8. Related events
9. Related gallery or creator content

Behavior:
- Sticky CTA on mobile
- Calendar add action if available
- Reminder picker: 2h before, 24h before, custom if supported

### 5. Galleries listing
Purpose:
- Dedicated gallery browsing

Required UI:
- Filter row: Nearby, New, Trending, By style, By creator
- Sort: Recommended, Newest, Popular
- Optional curated collections row

### 6. Gallery detail
Purpose:
- High-quality content browsing with context

Required UI:
- Hero/cover
- Gallery title
- Creator name and follow CTA
- Swipe/scroll media sequence
- Captions and commentary
- Save gallery
- Related events / creator page / more works

### 7. Saved
Purpose:
- Easy re-entry and intent management

Sections:
- Saved events
- Saved galleries
- Reminder-enabled events
- Following

### 8. Notification inbox
Purpose:
- Historical notification center

Sections:
- Reminders
- New from followed creators
- Nearby/trending suggestions
- Read/unread states

### 9. Search
Purpose:
- Direct retrieval for events, galleries, creators, venues

Search result tabs:
- All
- Events
- Galleries
- Creators
- Venues

### 10. Profile / preferences
Purpose:
- Edit taste, notification settings, location, privacy basics

Settings:
- Interests
- Notification preferences
- Location preference
- Saved/following overview

## UX guardrails
- Do not expose creator publishing tools in user surfaces
- One-tap save from cards
- Surface date/time above long descriptions
- Empty/loading/error states on every list/detail screen
- Minimum touch targets 44x44
- Accessible contrast and focus order
