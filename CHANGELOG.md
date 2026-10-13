# Changelog

All notable changes to Sweepy are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Card-layout PDF report (`engine/report.py`) is now the default output. It faithfully reproduces the reference layout with title + meta block, 4 cards per page, amber/slate highlighting, per-page subtitles, and a closing playbook table.
- Deterministic enrichment (`engine/enrich.py`) provides no-LLM fallbacks. It computes keyword-overlap `match_value`, resume-track routing, extracted summaries and requirements, comp, and a `"Not disclosed"` benefits placeholder.
- Deterministic sources (`engine/sources/`) for Ashby, Workable, and Built In NYC, with curated seed lists in `data/sources/`.
- Resume tracks (`resume.tracks`) for dual-targeting with keyword-based per-job routing.
- Thread-safe session store (`engine/session.py`) supports a hybrid stateful MCP flow. The flow runs `run_sweep` → `get_jobs` → `submit_judgments` → `render_report`. It also includes `import_jobs` for agent-found roles.
- Match provenance labeling: deterministic scores render as `NN% KEYWORD OVERLAP`; LLM-supplied scores render as `NN% MATCH`.
- `report.style: cards|legacy`, `report.cards_per_page`, `report.max_cards`, and `report.destinations` configuration.
- Workspace sandbox for MCP write paths (`SWEEPY_WORKSPACE`, `SWEEPY_ALLOW_EXTERNAL_WRITES`).
- Parallel URL validation (`ThreadPoolExecutor`, HEAD-first with GET fallback).
- Pipeline progress callbacks, wired through to MCP clients via `Context.report_progress`.
- `top_roles` projection and `include_roles` flag to trim the pipeline return payload.
- `unverified` column for jobs kept after a validation timeout.
- Input validation and consistent `status` fields on every MCP tool return.
- Timestamped report filenames (`YYYY-MM-DD-HHMMSS`) to prevent silent overwrites.
- Robust salary parsing in the wizard (`65000`, `65,000`, `$65,000`, `65k`).
- Unit test suite, `pyproject.toml` (ruff + pytest config), and GitHub Actions CI.

### Changed
- The card layout is now the default PDF (`report.style: cards`); the previous layout is retained as `report.style: legacy`.
- CSV/JSON export now includes the card schema columns.
- `export_report` renders the card layout when the source JSON contains card records.
- Replaced `print()` with `logging` across the engine and pipeline.
- Removed the `redirect_stdout` band-aid in favor of disciplined logging.
- Corrected the `remote_only` field, which the wizard previously wrote inverted.
- Fixed the `jobspy` country kwarg (`country_indeed`, replacing the invalid `country_alice`).
- Removed the `[50, 98]` match-score floor so zero-match jobs score near 0.
- `--version` now reports missing dependencies instead of crashing.
- Narrowed MCP exception handling and clamped `get_results` `limit` to 1-100.
- `get_results` now excludes `_export.json` files when selecting the latest sweep.
- Hybrid detection now uses a word-boundary regex on title/location only.

### Fixed
- Discovery failures are isolated per title and logged instead of killing the pipeline.
- Added dependency pins and a ToS/rate-limit disclaimer to the README.

## [1.5.0] - 2026-10-12

### Added
- Rebrand to **Sweepy**.
- Model Context Protocol (MCP) server (`server.py`) with `create_profile`, `run_sweep`, `get_results`, and `export_report` tools for AI assistant integration.
- `export_report` tool for regenerating reports without re-running discovery or scoring.

### Changed
- Redirected progress output to stderr in `create_profile` and `run_sweep` to keep the stdio protocol channel clean.
- Updated README and added `AGENTS.md` with tool reference and prompting patterns.

## [1.0.0] - 2026-10-01

### Added
- Core sweep engine modules: configuration wizard, scraper orchestration, URL validation, résumé scoring, and PDF/CSV/JSON reporting.
- Custom ATS platform sweep capability.
- Aligned engine architecture with the developer tutorial and overhauled docs.

## [1.1.0] - [1.4.0]

No separate release history exists in the repository for these versions; the project jumped from its initial release to 1.5.0.
