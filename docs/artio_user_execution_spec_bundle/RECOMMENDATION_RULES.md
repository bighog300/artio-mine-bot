# RECOMMENDATION_RULES

## Goal
Rank events and galleries so the user sees content that is timely, nearby, aligned with interests, and socially relevant.

## Phase 1 approach: deterministic rules
Use a weighted score from existing metadata only.

### Inputs
- User interests/tags
- User follows
- User saves
- User location
- Current time/date
- Event freshness/upcoming window
- Popularity proxies (views, saves, follows, attend intent)
- Content quality checks (has hero image, complete details)

### Event ranking factors
Score components:
- +30 if creator followed
- +25 if matches user interests or tags
- +20 if event within relevant date window
- +15 if near user location
- +10 if trending in region
- +5 if complete rich content
- -20 if event starts too soon for useful action window and no urgency rail
- -50 if cancelled or ended

Special rails:
- Tonight
- This week
- Nearby
- New from followed creators
- Trending near you

### Gallery ranking factors
- +30 if creator followed
- +25 if tags match user interests
- +15 if connected to a saved/upcoming event
- +10 if trending
- +5 if rich captions/commentary available

### Mix strategy for Explore
Default feed cadence:
- 2 event cards
- 1 gallery card
- repeat
Inject creator suggestions no more than every 10 cards.

### Cold-start logic
If no history:
1. Use onboarding interests
2. Use location and time relevance
3. Use popularity/trending
4. Diversify creators and categories

### Diversity rules
- No more than 2 consecutive items from same creator
- No duplicate gallery/event pair next to each other
- Minimum category spread in first 12 cards

## Phase 2 approach: personalized ranking upgrade
Add user behavior signals:
- clicks
- saves
- reminder creation
- gallery completion depth
- follows
- notification opens

Possible implementation:
- simple learning-to-rank or score calibration layer
- keep deterministic fallback for cold start and debugging

## Explainability
Return ranking_reason on cards, examples:
- “Because you follow this venue”
- “Popular near you this week”
- “Matches your interest in contemporary photography”
