# Changelog

All notable changes to Sweepy are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-10-13

### Added
- **Greenhouse and Lever run by default (no API key).** New deterministic fetchers (`engine/sources/greenhouse.py`, `engine/sources/lever.py`) sweep one full-content request per board/company and normalize results into the shared source schema.
- Seed lists `data/sources/greenhouse_boards.txt` (databricks, gitlab, cloudflare, robinhood) and `data/sources/lever_companies.txt` (leverdemo, spotify). Add `sources.greenhouse.boards` / `sources.lever.companies` to override them.
- `enabled: true` on all five deterministic sources (`greenhouse`, `ashby`, `lever`, `workable`, `builtinnyc`) in `config.sample.yaml` and `profiles/template_custom.yaml`.
- Sweepy now depends on `beautifulsoup4` directly. Every source module sends one shared `User-Agent` (`engine/sources/_common.py`).
- New README section "Default sources and how they run" documents the five default sources, Glassdoor-via-jobspy, the gating rules, and the bandwidth trade-off.
- New README sections cover résumé formatting and keyword selection, alongside a table of contents and GitHub alert callouts.

### Changed
- **v2.2.0 behavior change.** Every deterministic source now honors `sources.<x>.enabled` (default `true`) **and** `platforms.<x>` (default `true`) where a matching key exists. Setting `platforms.greenhouse/ashby/lever/workable: false` now also stops that seed source. Before v2.2.0, it filtered only `python-jobspy` results. Built In NYC has no `platforms` key, so it honors `enabled` alone. No flag default changed. Existing profiles now also discover the new Greenhouse and Lever postings unless you turn off a source.
- `discover_sources()` accepts a new optional `platforms` argument. `swee.py` passes the profile's `platforms` block through. The default (`None`) preserves prior behavior.
- Greenhouse and Lever fetches pre-filter by profile `titles` (substring match) during normalization to bound memory and time.
- Shared `html_to_text` and title-matching helpers now live in `engine/sources/_common.py` so the pre-filter and post-fetch filter stay in sync.
- `.vale.ini` now enables the `A11y` package and removes the `Diataxis` style name that stopped Vale with `E201`. The repo now tracks the file.
- Updated the stale `Sweepy/1.5` User-Agent in `ashby.py`, `workable.py`, and `builtinnyc.py` to the shared `Sweepy/2.2` constant.

### Fixed
- Sweepy now catches PNG rasterization errors, logs `[x] Could not build PNG`, and still writes CSV and JSON.

## [2.1.0] - 2026-10-13

### Added
- PNG export. Add `png` to `export.format` and Sweepy rasterizes the report PDF to `{name}.png` (single page) or `{name}_page{N}.png` (multi-page), applying the same `report.destinations` copy list as the PDF.
- `export_to_png()` in `engine/exporter.py` renders report PDFs to page images with `pymupdf`.
- `scripts/make_sample.py` now writes `docs/sample_report.png` next to `docs/sample_report.pdf`, so the committed artifact regenerates from one command.
- The `export_report` MCP tool accepts `png` in its `formats` list.

### Changed
- Requesting `png` also builds the PDF, because the PNG rasterizes the PDF pages. The PDF joins the generated report set.

## [2.0.1] - 2026-10-13

### Added
- Legal-specific seed sources in `data/sources/`: 7 Ashby orgs (crosby, normlaw, hargrove-firm, lawhive, legora, norm-ai), 5 Workable slugs (shegerianand-associates-1, harper-james, mangonelawfirm, legalvision, valiente-mott-injury-attorneys-1), 2 BuiltInNYC categories (jobs/legal, jobs/legal/search/paralegal)
- Updated `profiles/paralegal_nyc.yaml` with explicit legal sources demonstrating field customization
- "Customizing Sources for Your Field" section in README with examples for Legal, Technical Writing, Healthcare/Biotech, and custom platforms

### Changed
- Documentation clarifies how empty source lists fall back to seed files and how explicit lists override them

## [2.0.0] - 2026-10-13

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
- `docs/sample_report.{pdf,png}` now render the top 4 cards from a real `paralegal_nyc` sweep (live LinkedIn postings for Gordon Rees, Considine Search, CF Legal, Morgan Lewis), not a synthetic mock. Regenerate with `python scripts/make_sample.py`.
- The card layout is now the default PDF (`report.style: cards`); the previous layout is retained as `report.style: legacy`.
- CSV/JSON export now includes the card schema columns.
- `export_report` renders the card layout when the source JSON contains card records.
- Replaced `print()` with `logging` across the engine and pipeline.
- Kept a `_quiet_stdout()` guard in `server.py` as belt-and-braces to keep the MCP stdio channel clean.
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
