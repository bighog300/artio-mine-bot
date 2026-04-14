# Fix 3 — Migration Gating

## Problem
API may start before migrations complete.

## Required Change

Update docker-compose.yml:

api:
  depends_on:
    migrate:
      condition: service_completed_successfully

## Validation
- API only starts after migrations complete
- No schema mismatch errors
