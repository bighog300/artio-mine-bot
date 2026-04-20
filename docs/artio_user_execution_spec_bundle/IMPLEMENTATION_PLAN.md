# IMPLEMENTATION_PLAN

## Phase 1: user foundation
Goal:
Ship a reliable, coherent user experience for discovering and saving events/galleries.

Build order:
1. Data layer:
   - add saves, follows, reminders, notifications models if missing
   - add user interests and notification preferences
2. API layer:
   - /explore, /events, /galleries, /saved, /notifications
3. UI surfaces:
   - onboarding
   - explore
   - events list
   - event detail
   - galleries list
   - gallery detail
   - saved
   - notifications inbox
4. Interaction layer:
   - save/unsave
   - follow/unfollow
   - reminder create/delete
5. Deterministic recommendation service:
   - score + mix + diversify
6. Analytics instrumentation
7. QA and accessibility pass

## Phase 2: personalization and retention
Goal:
Improve relevance and return behavior.

Build order:
1. Behavioral signal capture
2. Recommendation ranking upgrades
3. Additional rails and ranking reasons
4. Frequency-capped recommendation notifications
5. Search refinement
6. Analytics dashboard readiness / event validation

## Non-goals
- Admin moderation UI
- Full ticketing ownership
- Advanced maps unless already present
- Machine-learning heavy recommender in first release
