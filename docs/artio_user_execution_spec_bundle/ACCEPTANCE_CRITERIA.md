# ACCEPTANCE_CRITERIA

## Phase 1
1. A new user can complete onboarding with interests, location preference, and notification preference.
2. A user can browse Explore, Events, and Galleries from primary navigation.
3. Event cards show image, title, date/time, location, and save state.
4. Gallery cards show cover image, title, creator, and save state.
5. A user can save or unsave an event from both feed and detail page in one tap.
6. A user can save or unsave a gallery from both listing and detail page in one tap.
7. A user can follow or unfollow a creator/venue from detail surfaces.
8. A user can set a reminder on an event using at least presets for 2h before and 24h before.
9. The Saved screen lists saved events and galleries separately.
10. Notification inbox shows read/unread notification history.
11. Explore feed returns mixed event/gallery content using deterministic recommendation rules.
12. Empty/loading/error states exist for all primary user surfaces.

## Phase 2
1. Explore ranking incorporates user behavior signals beyond onboarding interests.
2. Recommendation rails include “New from followed creators” and “Trending near you”.
3. Notification frequency caps and quiet hours are respected.
4. Ranking reason is visible in API payloads and can be surfaced in UI badges or helper text.
5. Search supports events, galleries, creators, and venues with tabbed results.
6. Analytics events are emitted for all core discovery, save, follow, reminder, and notification actions.
7. Cold-start users still receive a populated, diverse feed.
