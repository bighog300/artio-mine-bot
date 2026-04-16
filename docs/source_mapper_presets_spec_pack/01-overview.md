# Source Mapper Presets — Overview

## Goal

Add a reusable **preset** concept to the AI Source Mapper so operators can save good mapping findings, reuse them later, and clean up drafts without losing useful mapper output.

This feature should support three operator actions:

- **Create preset**
- **Delete preset**
- **Save mapper findings as preset**

## Current state

The current mapper supports draft/versioned findings through models and flows such as:

- source mapping drafts / versions
- page types
- mapping rows
- preview / sample runs
- publish / rollback

Findings are saved today as mapping versions and rows, not as reusable presets.

## Problem

Operators can review and publish findings, but they cannot save a successful draft as a reusable preset for the same source or similar sources.

## Proposed solution

Add a **Source Mapping Preset** feature that stores a reusable copy of approved or selected mapping findings from a draft/version.

Initial scope:

- source-local presets only
- create preset from draft/version findings
- list presets
- delete preset

Out of scope for v1:

- global/team-scoped preset libraries
- applying presets automatically during scan
- preset editing UI beyond create/delete
- versioning presets
