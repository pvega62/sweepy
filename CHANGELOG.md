# Changelog

Sweepy records every change in this file. It follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) for the format and [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the version numbers.

## [2.4.0] - 2026-10-15

### Added
- Self-update. `python swee.py --update` pulls the latest code and reinstalls `requirements.txt`; `python swee.py --check-update` reports whether a newer version exists. The update refuses to run when the checkout holds uncommitted changes. The setup wizard gains an "Update Sweepy" menu entry.
- `sweepy` console command. `pyproject.toml` now holds the packaging metadata, an editable install (`pip install -e .`) registers a `sweepy` entry point, and `sweepy --run` matches `python swee.py --run`. The version comes from `VERSION`, and the dependencies come from `requirements.txt`, so neither list runs twice.
- Wizard main menu. `python swee.py` opens a menu instead of starting the questionnaire, with choices to run a sweep, create a new profile, edit an existing profile, toggle debug logging, adjust scoring and scaling, add or edit aggregators, and convert a document to PDF. The header shows a bordered banner with the engine version and the active profile's job-title count, such as `Profile: Alex Rivera — 4 job titles`, or reads `Profile: (none loaded)` before a profile loads. The help screen lists every command flag plus links to the README and the documentation site.
- `--run` shortcut. `python swee.py --run` sweeps with the last saved profile, recorded in `profiles/.last_profile`, then falls back to the newest profile in `profiles/` and the conventional filenames.
- Wizard profile editing. The menu loads any YAML in `profiles/` into the review screen, keeps sections the wizard holds no question for (such as `sources`, `resume.synonyms`, and `report.destinations`), then lets you overwrite the file or save a new one. `--setup --profile profiles/your_profile.yaml` opens that file for editing straight away.
- Wizard resume-path hint. The wizard prints the shortcut that copies a file's full path, matched to your operating system: `Ctrl+Shift+C` in File Explorer on Windows 11, `Option+Command+C` in Finder on macOS, and `Ctrl+Shift+C` in most Linux file managers.
- Bonus document-to-PDF conversion. The wizard converts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf` files from the main menu, with or without a profile loaded. Text sources render as styled headings and bullets, an existing `.pdf` passes through or copies to a new path, and `.doc` renders through Microsoft Word. The wizard also offers to convert any document you enter as a resume path.
- Wizard navigation help. The wizard prints key controls and adds a "Show help" review-menu choice. Ctrl+C cancels setup cleanly.
- Wizard log viewing. A "Show recent logs" review-menu choice prints the newest debug-log entries without leaving the wizard, matching `python swee.py --logs`.
- Per-track resume scoring. Each job routes to one track and scores against that track's resume. The wizard now collects a resume path for each track.
- DOCX resume support in scoring. `create_profile` and `extract_resume_keywords` accept `.docx` as well as `.pdf`.
- Profile synonyms. `resume.synonyms` holds groups of interchangeable terms, and `create_profile` accepts a `synonyms` argument. Matching treats every member of a group as equivalent in both directions, so a posting that writes `documentation as code` matches a resume that writes `docs-as-code`.

### Changed
- Match scoring now measures coverage in both directions. Your keywords that appear in the posting supply 40% of the score. Requirements the posting states and your resume text already covers supply 60%. The old score divided resume-keyword hits by the full keyword list, which always ran low because a resume holds skills no given posting mentions. An earlier 26-posting comparison raised the mean from 17.8 to 31.4. Alias and priority refinements followed, and those still need evaluation against human relevance labels. The report label remains `NN% KEYWORD OVERLAP`. An LLM-supplied score renders as `MATCH`.
- Explicit required posting terms now count twice as much as unlabeled terms. Preferred terms count half as much. Matching also recognizes regular plural forms and a small built-in alias list.
- resume keyword extraction reads a `.docx` with `python-docx` instead of `pymupdf`. Previously `pymupdf` opened the `.docx` ZIP without error and returned reordered, partial text, so the same resume scored differently as DOCX and PDF: 17 of 109 keywords differed. Sweepy also flattens hard-wrapped lines before it reads tokens and phrases, which stopped a PDF's line breaks from fragmenting multi-word skills such as `First Aid`. On the same resume the two formats now agree on 81% of keywords, and the only remaining difference is one skill phrase the PDF wraps across two lines.
- Keyword extraction no longer splits skills on commas inside parentheses. `Adobe Suite (InDesign, Acrobat)` produced the unusable fragments `(indesign` and `acrobat)`. Parenthetical qualifiers now strip cleanly, and unbalanced fragments are rejected.
- Keyword extraction deduplicates case-insensitively, so `CSS`/`css`, `Docker`/`docker`, and `Javascript`/`javascript` no longer each consume a slot in the match denominator.
- Keyword extraction drops months, date ranges, employer names, and stopword-led fragments such as `and child abuse`, `additional skills`, and `april 2024 - present`. On a real resume, unmatchable keywords fell from 67% of the keyword set to 43%.
- Keywords are ordered by signal before the 60-keyword cap applies. The cap previously cut the alphabetically last terms, which discarded valid skills such as `python`, `react`, and `sql` while keeping fragments like `(indesign`.
- DOCX-to-PDF conversion preserves table text, so a converted DOCX and the original PDF extract the same content.
- The README gives readers a plain-language overview, a four-command quick start, sample reports, and links to the guides and reference. It moves seven deep-content pages into two Docusaurus groups. The existing pages reflect v2.4.0 behavior, and the docs spell "resume" without accents to match configuration keys.
- Every source module sends `Sweepy/2.4` in the `User-Agent` header, up from `Sweepy/2.3`.
- `data/sources/ashby_orgs.txt` drops three stale org slugs that returned HTTP 404 and logged a warning on every run: `stripe`, `google-deepmind`, and `braze`.

### Fixed
- The wizard can now attach a separate resume to each track instead of only the first track.
- URL validation no longer deletes live postings that answer with a rate-limit or bot-protection code. `engine.validator.check_url` now returns `valid`, `unverified`, or `dead`. Sweepy keeps unverified postings, such as 403, 408, 425, 429, and 5xx, and counts a posting expired only when the link is definitively gone. A measured HEAD request returned 429, while a GET on the same URL returned 200 with the full 312 KB job page. One run pruned 130 of 156 live postings this way.

## [2.3.0] - 2026-10-15

### Added
- DOCX-to-PDF conversion. `python swee.py --docx resume.docx` and a new `convert_docx` MCP tool rebuild a PDF from a Word document with python-docx + reportlab. If Word is available, the tool falls back to Microsoft Word through docx2pdf. A blank output path saves the PDF next to the source DOCX.
- Opt-in debug logging: `--debug`, `debug: true` in a profile, or `SWEEPY_DEBUG=1` write rotating logs under `logs/`. `python swee.py --logs` prints the latest entries. The wizard prompts you to turn logging on.
- Wizard review screen. After you answer, the wizard shows a summary of every answer and lets you edit any answer or start over before saving.
- Wizard track `color` values now accept a CSS name such as `navy`, not only a hex code. Any other value re-prompts.
- `skills/sweepy/SKILL.md`: a ready-to-install `/sweepy` skill for skill-aware CLIs, plus a README install prompt.

### Changed
- Deterministic keyword extraction now pulls a Skills section, frequent resume terms, and capitalized phrases into the match set, capped at 60.
- Scoring now searches the job title as well as the description, which improves no-LLM match accuracy.
- The jobspy fetcher uses `fetch_description=True` (replacing the deprecated `linkedin_fetch_description`), which restores LinkedIn and ZipRecruiter descriptions so those roles score instead of returning empty descriptions.
- Every source module now sends `Sweepy/2.3` in the `User-Agent` header, up from `Sweepy/2.2`.

### Fixed
- Ashby fetches treat an HTTP 404 (a stale org slug) as an empty result instead of raising through discovery.
- `report.max_cards: 0` now returns every card. The previous `or 24` fallback coerced `0` back to `24`, so an unlimited report truncated at 24 cards.

## [2.2.0] - 2026-10-13

### Added
- **Greenhouse and Lever run by default (no API key).** New deterministic fetchers (`engine/sources/greenhouse.py`, `engine/sources/lever.py`) sweep one full-content request per board/company and normalize results into the shared source schema.
- Seed lists `data/sources/greenhouse_boards.txt` (databricks, gitlab, cloudflare, robinhood) and `data/sources/lever_companies.txt` (leverdemo, spotify). Add `sources.greenhouse.boards` / `sources.lever.companies` to override them.
- `enabled: true` on all five deterministic sources (`greenhouse`, `ashby`, `lever`, `workable`, `builtinnyc`) in `config.sample.yaml` and `profiles/template_custom.yaml`.
- Sweepy now depends on `beautifulsoup4` directly. Every source module sends one shared `User-Agent` (`engine/sources/_common.py`).
- New README section "Default sources and how they run" documents the five default sources, Glassdoor-via-jobspy, the gating rules, and the bandwidth trade-off.
- New README sections cover resume formatting and keyword selection. The README also gains a table of contents and GitHub alert callouts.

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
- `scripts/make_sample.py` now writes `docs/sample_report.png` next to `docs/sample_report.pdf`. One command regenerates both committed artifacts.
- The `export_report` MCP tool accepts `png` in its `formats` list.

### Changed
- Requesting `png` also builds the PDF, because the PNG rasterizes the PDF pages. The PDF joins the generated report set.

## [2.0.1] - 2026-10-13

### Added
- Legal-specific seed sources in `data/sources/`. Ashby (6 orgs): crosby, normlaw, hargrove-firm, lawhive, legora, norm-ai. Workable (5 slugs): shegerianand-associates-1, harper-james, mangonelawfirm, legalvision, valiente-mott-injury-attorneys-1. BuiltInNYC (2 categories): jobs/legal, jobs/legal/search/paralegal.
- Updated `profiles/paralegal_nyc.yaml` with explicit legal sources demonstrating field customization.
- "Customizing Sources for Your Field" section in README with examples for Legal, Technical Writing, Healthcare/Biotech, and custom platforms.

### Changed
- Documentation clarifies how empty source lists fall back to seed files and how explicit lists override them.

## [2.0.0] - 2026-10-13

### Added
- Card-layout PDF report (`engine/report.py`) now produces the default output. It reproduces the reference layout with title + meta block, 4 cards per page, amber/slate highlighting, per-page subtitles, and a closing playbook table.
- Deterministic enrichment (`engine/enrich.py`) provides no-LLM fallbacks. It computes keyword-overlap `match_value`, resume-track routing, extracted summaries and requirements, comp, and a `"Not disclosed"` benefits placeholder.
- Deterministic sources (`engine/sources/`) for Ashby, Workable, and Built In NYC, with curated seed lists in `data/sources/`.
- Resume tracks (`resume.tracks`) for dual-targeting with keyword-based per-job routing.
- Thread-safe session store (`engine/session.py`) supports a hybrid stateful MCP flow. The flow runs `run_sweep` → `get_jobs` → `submit_judgments` → `render_report`. It also includes `import_jobs` for agent-found roles.
- Match provenance labeling. Deterministic scores render as `NN% KEYWORD OVERLAP`. LLM-supplied scores render as `NN% MATCH`.
- `report.style: cards|legacy`, `report.cards_per_page`, `report.max_cards`, and `report.destinations` configuration.
- Workspace sandbox for MCP write paths (`SWEEPY_WORKSPACE`, `SWEEPY_ALLOW_EXTERNAL_WRITES`).
- Parallel URL validation (`ThreadPoolExecutor`, HEAD-first with GET fallback).
- Pipeline progress callbacks, wired through to MCP clients via `Context.report_progress`.
- `top_roles` projection and `include_roles` flag to trim the pipeline return payload.
- `unverified` column for jobs kept after a validation timeout.
- Input validation and consistent `status` fields on every MCP tool return.
- Timestamped report filenames (`YYYY-MM-DD-HHMMSS`) to prevent silent overwrites.
- Salary parsing in the wizard accepts `65000`, `65,000`, `$65,000`, and `65k`.
- Unit test suite, `pyproject.toml` (ruff + pytest config), and GitHub Actions CI.

### Changed
- `docs/sample_report.{pdf,png}` now render the top 4 cards from a real `paralegal_nyc` sweep. The sweep captured live LinkedIn postings for Gordon Rees, Considine Search, CF Legal, and Morgan Lewis. Regenerate with `python scripts/make_sample.py`.
- The card layout now produces the default PDF style (`report.style: cards`). Sweepy keeps the previous layout as `report.style: legacy`.
- CSV/JSON export now includes the card schema columns.
- `export_report` renders the card layout when the source JSON contains card records.
- Replaced `print()` with `logging` across the engine and pipeline.
- Kept a `_quiet_stdout()` guard in `server.py` as a redundant safeguard for the MCP stdio channel.
- Corrected the `remote_only` field, which the wizard wrote inverted.
- Fixed the `jobspy` country kwarg (`country_indeed`, replacing the nonexistent `country_alice`).
- Removed the `[50, 98]` match-score floor so zero-match jobs score near 0.
- `--version` now reports missing dependencies instead of crashing.
- Narrowed MCP exception handling and clamped `get_results` `limit` to 1-100.
- `get_results` now excludes `_export.json` files when selecting the latest sweep.
- Hybrid detection now uses a word-boundary regex on title/location only.

### Fixed
- Sweepy isolates discovery failures per title and logs them instead of aborting the pipeline.
- Added dependency pins and a ToS/rate-limit disclaimer to the README.

## [1.5.0] - 2026-10-12

### Added
- Rebrand to **Sweepy**.
- Model Context Protocol (MCP) server (`server.py`) with `create_profile`, `run_sweep`, `get_results`, and `export_report` tools for AI assistant integration.
- `export_report` tool for regenerating reports without re-running discovery or scoring.

### Changed
- Redirected progress output to stderr in `create_profile` and `run_sweep` to keep the MCP stdio channel free of progress text.
- Updated README and added `AGENTS.md` with tool reference and prompting patterns.

## [1.0.0] - 2026-10-01

### Added
- The core modules handle the configuration wizard, scraper orchestration, URL validation, resume scoring, and PDF/CSV/JSON reporting.
- Custom ATS platform sweep capability.
- Aligned engine architecture with the developer tutorial and overhauled docs.

## Versions 1.1.0 through 1.4.0

The project jumped from 1.0.0 to 1.5.0. Versions 1.1.0 through 1.4.0 have no separate entries.
