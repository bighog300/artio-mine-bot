# Stability Sprint Goals

## Primary objective
Move Artio from feature-complete to operationally reliable.

## Desired outcome
After this sprint:
- developers trust CI
- migrations are safe to deploy
- failed schema changes are recoverable
- critical shipped loops are protected by tests
- releases are less fragile

## What success looks like
- no Prisma P3009 in fresh CI runs caused by repo migration history
- one clear test command path that works consistently
- branch protection can rely on real checks
- migration problems are diagnosable from CI output alone
- the three completed phases are protected from obvious regression
