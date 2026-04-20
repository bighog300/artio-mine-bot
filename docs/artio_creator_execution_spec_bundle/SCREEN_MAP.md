# SCREEN_MAP

## Navigation model for creators
Primary:
1. Dashboard
2. Content
3. Analytics
4. Public Page
5. Settings

Secondary:
- Create modal / route chooser
- Media library / uploader
- Preview mode
- Publish confirmation
- Archive/delete confirmation

## Screen inventory

### 1. Creator onboarding
Purpose:
- identify creator type and collect essentials

Fields:
- role: artist or venue owner
- display name
- avatar
- cover image
- bio
- city/location
- website/social links optional
- content goals optional

### 2. Dashboard
Purpose:
- snapshot and shortcuts

Modules:
- drafts
- upcoming events
- recent galleries
- quick create buttons
- summary analytics cards
- incomplete profile checklist

### 3. Content list
Tabs:
- Events
- Galleries
- Drafts
- Scheduled
- Published
- Archived

Actions:
- create
- edit
- preview
- duplicate optional
- archive
- delete

### 4. Create/Edit Event
Stepper:
1. Basics
2. Date & location
3. Media
4. Description
5. Preview
6. Publish

Required fields:
- title
- start date/time
- location or venue
- cover image/poster
- description
- categories/tags

Optional:
- ticket link
- end time
- price type
- linked gallery

### 5. Create/Edit Gallery
Stepper:
1. Basics
2. Media upload
3. Captions/commentary
4. Preview
5. Publish

Required:
- title
- cover image or first media
- minimum 1 media item

### 6. Public page editor
Purpose:
- control creator identity and layout

Sections:
- hero
- bio
- featured content
- upcoming events
- recent galleries
- contact/links
- venue info for venue owners

### 7. Public page view
Purpose:
- the user-facing mini-site for that creator/venue

### 8. Analytics
Purpose:
- feedback loop for creators

Metrics:
- profile views
- event views
- gallery views
- saves
- follows
- attend intent
- top content

### 9. Settings
Purpose:
- profile defaults
- notification preferences for creators if present
- connected links
- role details

## UX guardrails
- Always show draft/scheduled/published state clearly
- Always offer preview before publish
- Reduce form complexity with progressive disclosure
- Never require creator to understand internal system concepts
