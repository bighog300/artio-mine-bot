# AI-Optional Crawler Mode — Overview

## Goal

Refactor the current ingestion runtime so the crawler can operate **independently of OpenAI** when a usable runtime map already exists for the source.

This includes cases where the source already has:
- a valid `structure_map`
- a previously saved and applied mapping preset
- deterministic crawl/extraction rules sufficient for classification and extraction

## Intended behavior

### If a source already has a usable runtime map
The system should:
- skip OpenAI site mapping
- skip OpenAI classification when deterministic rules are sufficient
- skip OpenAI extraction when deterministic rules are sufficient
- allow the worker/job to run without an OpenAI API key
- crawl/extract as a regular deterministic crawler

### If a source does not have a usable runtime map
The system may:
- run OpenAI-assisted mapping if configured and available
- or fail clearly with a “no runtime mapping available” error

## Current problems in the repo

The current runtime is still OpenAI-dependent in several ways:
- production startup requires `OPENAI_API_KEY`
- worker always instantiates `OpenAIClient`
- `run_full_pipeline()` always starts with AI site mapping
- saved presets are persisted, but not used as runtime crawl/extraction configs
- extraction still falls back to AI when deterministic classification misses

## Product intent

A saved map/preset should let the source behave like a normal crawler:
- follow the source’s known structure
- classify pages deterministically
- extract mapped fields deterministically
- continue without OpenAI

## Scope

This spec covers:
- making OpenAI optional at runtime
- making presets/runtime maps usable by the crawler
- skipping AI mapping when runtime config already exists
- deterministic-first classification/extraction
- operator visibility for AI-free deterministic runs
