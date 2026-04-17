# Entity + Media Linking Spec

## Goal

Treat media capture and entity linking as first-class parts of preset-driven mining and enrichment.

## Required entity types

Initial focus:
- Artist
- Event / Exhibition
- Venue
- MediaAsset

## Required linking behavior

### Artist
Link:
- profile image
- gallery images
- related events

### Event / Exhibition
Link:
- hero image
- gallery images
- featured artists
- venue

### Venue
Link:
- venue image(s)
- events hosted at venue

## Media asset roles
Use roles such as:
- `profile`
- `thumbnail`
- `hero`
- `gallery`
- `document`
- `logo`

## Merge behavior
Prefer:
- detail pages over index cards
- richer field values over sparse ones
- explicit mapped image roles over generic linked images

## Acceptance criteria

- deterministic mining can capture and link media
- enrichment can add missing media links to existing records
- artists/events/venues become more complete through repeated runs
