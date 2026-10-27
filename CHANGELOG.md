# Changelog

Sweepy records every change in this file. It follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) for the format and [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the version numbers.

## [Unreleased]

### Added
- Portfolio support across the MCP, the wizard, the report, and the exports. A profile gains a `portfolio` block with one source per resume track. Each source takes an online URL, a local `.pdf`, `.docx`, `.md`, `.txt`, or `.html` file, or an explicit `pieces` list. Sweepy reads each portfolio once per sweep and lists its pieces on every card. The MCP server instruction directs the agent to collect a portfolio before `create_profile`. `create_profile` accepts `resume_tracks` and `portfolios`. The new `set_portfolio` tool updates a saved profile. `submit_judgments` takes `portfolio_highlight`. Cards, the report header, the default playbook, and the new `portfolio_url`, `portfolio_pieces`, and `portfolio_highlight` CSV columns show the pieces to send. The wizard adds a portfolio step after the resume tracks. `swee.py` adds `--portfolio` and `--portfolio-track` to a headless setup. When a portfolio host blocks the fetch, the card keeps the link and skips the piece list. The sweep continues.
- Two-sided card assessment. `submit_judgments` now takes a `concerns` field beside the `alignment` highlight. Every assessed posting then states what works against the candidate. The report prints the pair on one line: teal for the tip, red for the concern. The CSV export gains a `concerns` column. Card enrichment fills a deterministic fallback from `missing_skills` for keyword-only reports and for cards no agent assessed. `submit_judgments` and `get_jobs` now tell the calling model to supply both sides.

### Fixed
- Full-posting scanning. `engine/enrich.py` collapsed every posting into one line before reading it, so a card's Overview and Key Requirements came from the opening company paragraph and section headings never matched. `_strip_html` now keeps block-level line breaks, and the new scans read requirements from labeled sections, bullet and numbered lists, or an inline sentence anywhere in the posting. `export.description_chars` still controls the excerpt written to the CSV and JSON, so reports keep the short text.
- Escaped markup on Greenhouse boards. Entities were decoded after tag stripping, so cards carried literal `<div>` and `<li>` text. Decoding now runs first.

### Added
- Description pay fallback. When a board omits pay fields, the card now shows a range read from the posting text. `engine/salary.py` extracts annual, hourly, and monthly figures, rejects amounts tied to bonuses, equity, and funding, and keeps the posting's unit on the card (`$45 - $55 / hour`). The `search.min_salary` floor compares annualized pay. An hourly rate converts at 2,080 hours. Sweepy also maps the pay interval an aggregator reports, such as JobSpy's hourly rows. `search.salary_from_description` (default `true`) turns the fallback off, and the CSV export gains a `salary_period` column.
- Cross-run deduplication. Sweepy records every posting it reports in `~/.sweepy/history.db` and hides those postings on later sweeps. A daily run returns new roles instead of yesterday's list. The `history` profile block controls `enabled`, `retention_days` (default 4), `match` (`url+role` or `url`), and `path`. Matching uses canonical URLs, with tracking parameters and fragments removed, and falls back to normalized title, company, and location. Only postings that pass URL validation enter history.
- `sweepy --include-seen` reports earlier postings for one run, `sweepy --reset-history` clears a profile's history, and `--history-days`/`--no-history` set the behavior during a headless setup. The MCP `run_sweep` tool gains `include_seen`, `create_profile` gains `history_config`, and the new `clear_history` tool forgets a profile's history. `SWEEPY_HISTORY_PATH` moves the database.
- `get_sweep_status` MCP tool. `run_sweep` now runs the pipeline on a background thread and answers within `wait_seconds` (default 45) instead of blocking for the whole sweep. A long sweep returns `sweep_status: "running"` with a `job_id`, and `get_sweep_status` waits in bounded slices until the sweep completes. The sweep keeps running when the client disconnects, and a repeated `run_sweep` for the same profile rejoins the running job instead of scraping twice. `SWEEPY_MCP_WAIT_SECONDS` caps the wait for hosts with tighter tool timeouts.
- Cross-board duplicate detection matches repeated URLs plus normalized title, company, and location. Pass `sweepy --run --no-dedupe` or `deduplicate=false` to the MCP `run_sweep` tool to keep duplicate postings for one run without changing the profile.
- Job-tracking CSV columns. `export.tracking` (default `true`) appends `date_applied`, `status`, `interview_stage`, `offer_amount`, `offer_date`, `follow_up_date`, `contact`, and `notes` after `description`. Each sweep reads the 20 newest CSVs for the same profile and copies your entries into the new export. Sweepy matches on canonical URL with a title/company/location fallback. The profile wizard includes a question about the columns, the review screen offers a toggle, **Sweep Settings** toggles them, `--job-tracking`/`--no-job-tracking` covers headless setup, `create_profile` gains `job_tracking`, and `export_report` gains `job_tracking`. Every bundled profile under `profiles/` sets `export.tracking: true`.
- Agent assessment becomes the MCP default. `report.assessment: "agent"` makes `render_report` refuse a mixed report and return `unassessed_job_ids` and `unassessed_titles`. Keyword overlap alone can't produce a card directory. `report.assessment: "keyword"` keeps the old behavior, `create_profile` accepts `assessment`, and `run_sweep` reports `assessment_mode`, `assessment_required`, and `assessed_count`. `SWEEPY_REQUIRE_JUDGMENTS=1` applies the gate to every profile and to `export_report`.
- `submit_judgments` accepts a `judgments` list. An assistant assesses every card in one call instead of one request per role. A batch returns `applied`, `jobs`, and `rejected`.
- CSV posting excerpts and scored columns. Cards now include a `description` excerpt cut on a sentence boundary at `export.description_chars` characters (default `1000`; `0` writes the full posting text), so the CSV and JSON exports no longer leave that column blank. Columns that used to pad with empty values (`match_score`, `badge`, `unverified`, `min_amount`, `max_amount`, `currency`, `key_matches`, `missing_skills`, `playbook`) now repeat the card value.

### Changed
- `scripts/make_sample.py` gains `--complete-only` and `--renumber`. The committed sample now shows only cards with a company and posting text. `docs/sample_report.{pdf,png}`, the Docusaurus copies, and the terminal transcripts in `docs/sweepy/first-sweep.mdx` now come from a fresh `paralegal_nyc` sweep (137 roles, 36 CSV columns).
- The bundled samples declare synonym groups. `profiles/paralegal_nyc.yaml` and `config.sample.yaml` each list the same five interchangeable-term groups, and the configuration reference and resume-tips guide quote those groups. `profiles/template_custom.yaml` now shows one commented group as an example.
- `profiles/template_custom.yaml` now works as a fill-in template for a direct run. Copy it, replace the four REQUIRED values, then run `sweepy --profile profiles/your_copy.yaml`. The wizard and the MCP server both become optional, and the file documents every supported setting with its default.
- `render_report` playbook text is now plain prose. Sweepy escapes ampersands and angle brackets and turns newlines into line breaks. It also renders `**bold**` as bold text. Callers no longer write ReportLab markup. The text saves to `report_session.json` and a later render reuses it instead of reverting to the generated playbook. A finished sweep clears the saved text, because it replaces every card.
- The playbook box reserves its height only on the page with the final card. Pages before it now fill to `report.cards_per_page` instead of losing a card slot to a box that renders later.
- Sweeps report new postings by default. Existing profiles inherit `history.enabled: true` with a four-day window. Set `history.enabled: false` in the profile, or pass `--include-seen`/`include_seen=true`, to report every posting on every run.
- Align the README, agent guidance, Sweepy skill, and sample profile with current command-line and MCP behavior, including separate `jobdrop` installation and PDF/DOCX resume support.
- Plain launchpad subtitles. Each main-menu tile now describes its action in a few plain words that fit the card. **Sweep Settings** shows **Ranking, cards, tracking**. **Sweepy's Toolbox** shows **Edit profile, logs, help**. Both fit without cutting off mid-word. The README, sample profile, engine requirements, and install guidance use the current tile names.

### Fixed
- Built In NYC cards now include company, workplace, location, and pay. The listing parser reads `data-id="company-title"` and the icon labels for workplace, location, and salary. Relative links resolve against the site root instead of the search page, which fixes apply links that pointed at `jobs/legal/search/paralegal/job/...`, and city links such as `/jobs?city=Austin` no longer parse as postings. Built In challenges detail pages after a few requests. `sources.builtinnyc.detail_pages` (default `false`) opts into reading each posting's `JobPosting` JSON-LD for the full text, one page at a time, stopping at the first challenge.
- Submitting a judgment now renumbers `rank` by the assessed score and clears the derived `page` and `page_theme` labels. Reports headed "Highest to Lowest Match %" no longer list a lower-scored card before a higher one, and page subtitles follow the new order. Ties keep their previous relative order.
- MCP `run_sweep` without `profile_path` now runs the last saved profile instead of jumping to a tracked preset such as `profiles/paralegal_nyc.yaml`. It resolves the profile the way `sweepy --run` does. Sweepy reads the recorded profile, then the newest YAML in `profiles/`. If neither exists, it falls back to the conventional filenames.
- `recent_log_lines` now breaks equal file times by log name. It returns the newest log when two runs create files inside one filesystem timestamp tick.

## [3.0.0] - 2026-10-17

### Added
- Multi-engine orchestrator. `engine/discovery.py` now dispatches through `engine/adapters/` on one `ScraperAdapter` contract instead of calling JobSpy and the native readers in sequence. Enabled engines start together. A sweep then takes about as long as the slowest engine.
- Downloadable engines. `hirehunt` adds India-first boards plus LinkedIn and Indeed through their APIs. `openroles` reads Greenhouse, Lever, Ashby, and Workday boards you name. `jobdrop` reaches 33 boards, including Google, Wellfound, iCIMS, Dice, and USAJobs. `apify` runs managed actors. Each one declares the boards it scrapes in `engine/engines.py`.
- Engine downloads inside the wizard. **Sweepy's Toolbox** then **Download job engines** prints a status table and lists the boards each engine scrapes. It installs on confirmation with a `--user` retry and an exact retry command. Selecting a missing engine while building a profile offers the download in place. Installing never enables an engine on its own.
- `sweepy --list-engines` and `sweepy --install-engines all|jobdrop,openroles`. Both run without a profile.
- `sweepy --setup --non-interactive` builds or updates a profile from flags: `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, `--no-cache`, `--name`, `--titles`, `--location`, `--resume`.
- Per-engine timeouts and a circuit breaker. `orchestrator.timeout_per_source_seconds` bounds each engine, and `orchestrator.circuit_breaker` skips an engine after 5 consecutive failures for 30 seconds.
- Discovery cache. `cache.enabled` and `cache.ttl_seconds` store normalized results in SQLite under `~/.sweepy/cache.db`. The key covers the query, the enabled engines, and their settings, and the payload is JSON rather than pickle.
- Normalized output. Every engine frame maps onto one schema with `title`, `company`, `location`, `url`, `source`, `posted_at`, salary fields, `description`, `remote`, `employment_type`, and `raw`. Results dedupe by URL, then by role details when a URL is missing.
- `skipped_sources` in the `run_sweep` MCP response. Failures and timeouts appear as `{"name": ..., "reason": ...}` entries, and the sweep still returns success.
- `sources_config` on the `create_profile` MCP tool. It merges into the generated `sources` block and validates each enabled engine first.
- `cache_config` and `orchestrator_config` on `create_profile`. MCP callers can now tune cache lifetime, per-engine timeouts, and circuit-breaker behavior.
- Wizard engine management. **Manage job engines** in the toolbox, review-screen choices for engines and engine performance, per-engine prompts, masked proxy entry, and a "Job engines" help screen.
- Wizard navigation. Each submenu opens with **← Back**, and Esc goes up exactly one level. From a question, Esc returns to the previous answer. From a submenu, Esc returns to its parent menu. From the toolbox menu, Esc returns to the launchpad. From the launchpad, Esc exits the wizard. The toolbox now runs as its own menu level, so backing out of engine, aggregator, or help screens returns to the toolbox instead of the launchpad. Ctrl+C still quits from anywhere.
- Full-board platform picker. The profile wizard's platform step now lists all 63 boards Sweepy can search, grouped under the engine that reads them. Counts per engine: `jobspy` 8, `ats` 5, `hirehunt` 12, `openroles` 4, `jobdrop` 33, `apify` 1. Each row shows a tag, such as `Indeed  [jobspy · built in]` or `Wellfound  [jobdrop · needs download]`, and the tag appears before the user commits to the choice. Choosing boards from an engine that has no local install prints the install command, and an installed engine reads `installed`. Reopening a profile shows its current boards already ticked. `engine/engines.py` grows `BOARD_CATALOG` and `board_summary()` as the one source behind the picker and each engine's own prompt.
- Launchpad grid. The main menu gains an **Exit Sweepy** tile, which balances the launchpad grid into even rows. The trailing tile centers itself, which keeps any future odd tile count balanced.
- `jobdrop` compatibility guard. `jobdrop` pins `curl-cffi<0.8` while JobSpy requires `curl_cffi>=0.16.2`. A plain `pip install` of both fails. The pin is stale: verified against curl_cffi 0.16.3, which still includes every impersonation profile `jobdrop` uses, and both engines returned live postings. `--install-engines all`, the wizard's install-all action, and `missing_engines()` now skip `jobdrop`. Adding `--allow-engine-conflicts` installs it with `--no-deps` and then resolves its other requirements, so `curl_cffi` stays at JobSpy's version. `--list-engines` marks the conflict, `jobdrop` moved into its own `jobdrop` extra and `requirements-jobdrop.txt`, and `pip check` still reports its stale bound.
- Disk footprint documented. The README records measured sizes: 290 MB for the core install and about 320 MB with every compatible engine. Forcing `jobdrop` in raises the total to 715 MB. Playwright's Chromium adds about 710 MB, and Camoufox's patched Firefox adds more.

### Changed
- Optional engines are extras. `requirements-engines.txt` holds `hirehunt`, `openroles`, `jobdrop`, and `apify-client`, and `pyproject.toml` publishes `engines`, `apify`, and `all-engines` extras. Adapters import their library at call time and raise an install message instead of breaking startup.
- `sweepy --update` reinstalls the optional engines a checkout already had. A code pull doesn't strand them.
- Descriptions stay on by default. Scoring needs posting text. Set `fetch_descriptions: true` as the default for JobSpy and jobdrop. Turning it off trades match quality for speed.
- JobSpy sends a current Chrome User-Agent by default and accepts a per-engine override.
- `discover_jobs()` and `discover_sources()` keep their signatures and return contracts as thin wrappers over the orchestrator. Existing callers and tests keep working.
- Profiles without `sources.enabled` resolve to JobSpy plus the native ATS readers. Legacy board booleans under `sources.jobspy` still work.

### Fixed
- One failing engine no longer empties a sweep. Sweepy isolates every engine error, timeout, and open circuit, logs the engine name, and reports the result in `skipped_sources`.
- Concurrent runs no longer collide in the cache. Semaphores belong to each call rather than the module, and cache keys include engine settings.
- The MCP SDK pins to `mcp==1.30.0`. The 2.x SDK serves only the 2026-07-28 protocol era over stdio. Visual Studio Code Copilot probes `server/discover`, and the first modern request locks the connection to that era. The `2025-11-25` `initialize` fallback then fails with `-32022`. Version 1.30.0 answers the 2025-11-25 handshake directly and negotiates cleanly on the first request. `requirements.txt` repeats the note beside the pin.

## [2.4.0] - 2026-10-15

### Added
- Self-update. `python swee.py --update` pulls the latest code and reinstalls `requirements.txt`. `python swee.py --check-update` reports whether a newer version exists. The update refuses to run when the checkout holds uncommitted changes. The setup wizard gains an "Update Sweepy" menu entry.
- `sweepy` console command. `pyproject.toml` now holds the packaging metadata, an editable install (`pip install -e .`) registers a `sweepy` entry point, and `sweepy --run` matches `python swee.py --run`. The version comes from `VERSION`, and the dependencies come from `requirements.txt`.
- Wizard main menu. `python swee.py` opens a menu instead of starting the questionnaire, with choices to run a sweep, create a new profile, edit an existing profile, toggle debug logging, adjust scoring and scaling, add or edit aggregators, and convert a document to PDF. The header shows a bordered banner with the engine version and the active profile's job-title count, such as `Profile: Alex Rivera — 4 job titles`, or reads `Profile: (none loaded)` before a profile loads. The help screen lists every command flag plus links to the README and the documentation site.
- `--run` shortcut. `python swee.py --run` sweeps with the last saved profile, recorded in `profiles/.last_profile`, then falls back to the newest profile in `profiles/` and the conventional filenames.
- Wizard profile editing. The menu loads any YAML in `profiles/` into the review screen, keeps sections the wizard skips (such as `sources`, `resume.synonyms`, and `report.destinations`), then lets you overwrite the file or save a new one. `--setup --profile profiles/your_profile.yaml` opens that file for editing straight away.
- Wizard resume-path hint. The wizard prints the shortcut that copies a file's full path, matched to your operating system: `Ctrl+Shift+C` in File Explorer on Windows 11, `Option+Command+C` in Finder on macOS, and `Ctrl+Shift+C` in most Linux file managers.
- Bonus document-to-PDF conversion. The wizard converts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf` files from the main menu. A profile is optional. Text sources render as styled headings and bullets, an existing `.pdf` passes through or copies to a new path, and `.doc` renders through Microsoft Word. The wizard also offers to convert any document you enter as a resume path.
- Wizard navigation help. The wizard prints key controls and adds a "Show help" review-menu choice. Ctrl+C cancels setup cleanly.
- Wizard log viewing. A "Show recent logs" review-menu choice prints the newest debug-log entries without leaving the wizard, matching `python swee.py --logs`.
- Per-track resume scoring. Each job routes to one track and scores against that track's resume. The wizard now collects a resume path for each track.
- DOCX resume support in scoring. `create_profile` and `extract_resume_keywords` accept `.docx` as well as `.pdf`.
- Profile synonyms. `resume.synonyms` holds groups of interchangeable terms, and `create_profile` accepts a `synonyms` argument. Matching treats every member of a group as interchangeable in both directions. A posting that writes `documentation as code` matches a resume that writes `docs-as-code`.

### Changed
- Match scoring now measures coverage in both directions. Your keywords that appear in the posting supply 40% of the score. Requirements the posting states and your resume text already covers supply 60%. The old score divided resume-keyword hits by the full keyword list, which always ran low because a resume holds skills no given posting mentions. An earlier 26-posting comparison raised the mean from 17.8 to 31.4. Alias and priority refinements followed. Those still need evaluation against human relevance labels. The report label stays `NN% KEYWORD OVERLAP`. An LLM-supplied score renders as `MATCH`.
- Explicit required posting terms now count twice as much as unlabeled terms. Preferred terms count half as much. Matching also recognizes regular plural forms and a small built-in alias list.
- resume keyword extraction reads a `.docx` with `python-docx` instead of `pymupdf`. `pymupdf` used to open the `.docx` ZIP without error and return reordered, partial text. The same resume scored differently as DOCX and PDF: 17 of 109 keywords differed. Sweepy also flattens hard-wrapped lines before it reads tokens and phrases, which stopped a PDF's line breaks from fragmenting multi-word skills such as `First Aid`. On the same resume the two formats now agree on 81% of keywords, and the only remaining difference is one skill phrase the PDF wraps across two lines.
- Keyword extraction no longer splits skills on commas inside parentheses. `Adobe Suite (InDesign, Acrobat)` produced the unusable fragments `(indesign` and `acrobat)`. Parenthetical qualifiers now strip cleanly, and Sweepy rejects unbalanced fragments.
- Keyword extraction deduplicates case-insensitively. `CSS`/`css`, `Docker`/`docker`, and `Javascript`/`javascript` no longer each consume a slot in the match denominator.
- Keyword extraction drops months, date ranges, employer names, and stopword-led fragments such as `and child abuse`, `additional skills`, and `april 2024 - present`. On a real resume, unmatchable keywords fell from 67% of the keyword set to 43%.
- Sweepy orders keywords by signal before the 60-keyword cap applies. The cap used to cut the alphabetically last terms, which discarded valid skills such as `python`, `react`, and `sql` while keeping fragments like `(indesign`.
- DOCX-to-PDF conversion preserves table text. A converted DOCX and the original PDF extract the same content.
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
- `report.max_cards: 0` now returns every card. The previous `or 24` fallback coerced `0` back to `24`. An unlimited report no longer truncates at 24 cards.

## [2.2.0] - 2026-10-13

### Added
- **Greenhouse and Lever run by default (no API key).** New deterministic fetchers (`engine/sources/greenhouse.py`, `engine/sources/lever.py`) sweep one full-content request per board/company and normalize results into the shared source schema.
- Seed lists `data/sources/greenhouse_boards.txt` (databricks, gitlab, cloudflare, robinhood) and `data/sources/lever_companies.txt` (leverdemo, spotify). Add `sources.greenhouse.boards` / `sources.lever.companies` to override them.
- `enabled: true` on all five deterministic sources (`greenhouse`, `ashby`, `lever`, `workable`, `builtinnyc`) in `config.sample.yaml` and `profiles/template_custom.yaml`.
- Sweepy now depends on `beautifulsoup4` directly. Every source module sends one shared `User-Agent` (`engine/sources/_common.py`).
- New README section "Default sources and how they run" documents the five default sources, Glassdoor-via-jobspy, the gating rules, and the bandwidth trade-off.
- New README sections cover resume formatting and keyword selection. The README also gains a table of contents and GitHub alert callouts.

### Changed
- **v2.2.0 behavior change.** Every deterministic source now honors `sources.<x>.enabled` (default `true`) **and** `platforms.<x>` (default `true`) where a matching key exists. Setting `platforms.greenhouse/ashby/lever/workable: false` now also stops that seed source. Before v2.2.0, it filtered only `python-jobspy` results. Built In NYC has no `platforms` key and honors `enabled` alone. No flag default changed. Existing profiles now also discover the new Greenhouse and Lever postings unless you turn off a source.
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
- Hybrid detection now uses a word-boundary regular expression on title and location only.

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
