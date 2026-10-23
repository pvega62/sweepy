# Sweepy agent guidelines

Guidelines for AI assistants (such as Antigravity, Claude, and Cursor) interacting with the Sweepy job search engine.

## Overview

Sweepy discovers, filters, scores, and exports job postings from Applicant Tracking Systems (Greenhouse, Ashby, Lever, Workable) and aggregators.

AI assistants can interact with Sweepy through:
1. **MCP tools** via `server.py` (`stdio` transport).
2. **Direct commands** via `swee.py`.

---

## Tool reference and sequencing

Sweepy exposes MCP tools through `server.py` in two workflows. The one-shot flow returns
deterministic keyword-overlap scores. The hybrid stateful flow lets the calling LLM
assess each role against the candidate's resume and available job evidence.

**Default for user-requested job searches: LLM-assisted hybrid flow**

```text
create_profile → run_sweep → get_sweep_status (until completed) → get_jobs → assess roles → submit_judgments → render_report
```

`run_sweep` answers in bounded time. A live sweep runs in the background, so a long
scrape returns `sweep_status: "running"` with a `job_id` instead of blocking the client
past its tool timeout. Poll `get_sweep_status` until it reports `completed`.

Do not stop at `run_sweep` or present its `KEYWORD OVERLAP` scores as LLM matches.
`run_sweep` performs discovery and deterministic keyword scoring; the MCP does not invoke
the model automatically. The assistant must review the available evidence for each role,
compare it with the resume and user preferences, and submit an independent judgment with
`submit_judgments`. Do not copy a keyword score into `match_pct` or invent missing job
requirements. If the available evidence cannot support a responsible assessment, disclose
that limitation and label the score as keyword overlap rather than an LLM match.

`run_sweep` removes repeated URLs and same-role listings across boards by default. The
MCP caller can pass `deduplicate=false` for one run without changing the profile.

`run_sweep` also reports only postings the user has not received before. Sweepy records
each reported posting in `~/.sweepy/history.db`, scoped per profile, and hides it for
`history.retention_days` (4 by default). Pass `include_seen=true` to review earlier
postings for one run. When every discovered posting is a repeat, the payload reports
`previously_seen_count` with zero new cards and a `message`; relay that instead of
presenting the sweep as a failure.

Use the keyword-only one-shot flow only when the user explicitly requests deterministic
results or when the assistant cannot assess roles responsibly:

```text
create_profile → run_sweep → get_results → export_report (optional)
```

### Use LLM judgment to compensate for scraper limits

Treat Sweepy's output as a useful, non-exhaustive candidate set—not as a complete
or authoritative account of the job market. The LLM should add evidence-based
verification and coverage where its host provides search tools:

- After `run_sweep`, inspect `skipped_sources` and `engines_not_enabled`. Explain
  material failures or missing engines; do not imply that every source returned data.
- Use `get_jobs` to review the full set before presenting recommendations. Check each
  posting against the user's titles, location, workplace preferences, salary floor,
  must-have skills, and resume. Correct deterministic match scores only with an
  independent, evidence-based `submit_judgments` assessment.
- When the host provides web or search tools, use them to verify promising listings
  against employer career pages or the linked ATS, and search for relevant roles that
  Sweepy missed. Use `import_jobs` to add only verified, non-duplicate postings to the
  same report. Pass `validate: true` for an additional URL check.
- Treat HTTP 403, 429, timeouts, and similar access blocks as unverified—not proof that
  a listing expired. Prefer checking the employer's career page or another accessible
  source. Keep the listing qualified as unverified if you cannot confirm its status.
- Never invent a posting, active status, compensation, requirements, or resume evidence.
  If the host has no suitable search tools, or sources remain inaccessible, report the
  search as partial and state what you could not verify. Do not retry an unchanged,
  failing sweep repeatedly; retry only after a meaningful correction to the profile,
  source configuration, or transient failure condition.
- After importing and judging roles, call `render_report`. Summarize supplemental
  research and unresolved source failures separately from Sweepy's scraped results.

### 1. `create_profile`
Builds and saves a YAML configuration profile in the `profiles/` directory.

- **When to call.** Call when the user names target job roles, a preferred location, or a résumé path. Call it again to update search preferences.
- **Key parameters**:
  - `name`: candidate's full name.
  - `titles`: list of job titles to search for (such as `["Technical Writer", "Documentation Engineer"]`).
  - `location`: target city, state, or metro area (such as `"New York, NY"`).
  - `resume_path`: path to the candidate PDF or DOCX résumé (absolute or relative).
  - `remote_only`: set `True` if the candidate accepts only remote roles. Defaults to `False`.
  - `include_hybrid`: set `True` to include hybrid roles alongside remote or on-site roles. Defaults to `True`.
  - `min_salary`: lowest acceptable base salary as an integer (such as `90000`). Use `0` if unconstrained.
  - `must_have_skills`: optional list of mandatory keywords to boost ranking (such as `["API Documentation", "Markdown"]`).
  - `platforms`: optional dictionary enabling or disabling scrapers (such as `{"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}`).
  - `sources_config`: optional dictionary merged into the profile's `sources` block (such as `{"enabled": ["jobspy", "openroles"], "openroles": {"companies": ["figma"]}}`). Every enabled engine validates before the file is written, so a bad block returns an error instead of a broken profile.
  - `cache_config`: optional cache settings with `enabled` and `ttl_seconds` fields.
  - `orchestrator_config`: optional `timeout_per_source_seconds` and `circuit_breaker` settings (`failure_threshold`, `cooldown_seconds`).
  - `history_config`: optional cross-run settings with `enabled`, `retention_days` (default `4`), `match` (`url` or `url+role`), and `path` fields.
  - `job_tracking`: set the CSV tracking columns on or off. Defaults to `True`.
  - Board keys: `BOARD_CATALOG` in `engine/engines.py` lists every searchable board per engine (8 `jobspy`, 5 `ats`, 12 `hirehunt`, 4 `openroles`, 33 `jobdrop`, 1 `apify`). The wizard's platform step reads that catalog, which means a new board doesn't need extra UI code. Headless callers set boards through `sources_config` (`sources.jobspy.sites`, `sources.hirehunt.sources`, `sources.openroles.ats`, `sources.jobdrop.sites`).
  - `output_filename`: optional explicit destination YAML path. Defaults to `profiles/{name}_{title}.yaml`.

### 2. `run_sweep`
Executes the 5-stage discovery pipeline: discovery, validation, deterministic keyword scoring, report generation, and CSV/JSON export. It populates the session with preliminary cards and returns their ids. This tool does not run LLM assessment; continue through `get_jobs`, `submit_judgments`, and `render_report` for the default user-requested search workflow.

A live sweep needs minutes of board scraping, so the pipeline runs on a background thread and the tool call waits at most `wait_seconds` (default `45`, tunable through `SWEEPY_MCP_WAIT_SECONDS`). While the sweep runs, the response reads `sweep_status: "running"` and carries a `job_id`.

- **When the response says `running`.** Call `get_sweep_status` with that `job_id` and repeat until it returns `sweep_status: "completed"`. Then continue with `get_jobs`. Each call waits at most its own `wait_seconds`, so no single request outlives the client's tool timeout.
- **Disconnects are safe.** The sweep keeps running when the client drops the request and persists `report_session.json` on completion, so `get_jobs` can pick the results up afterwards.
- **Repeated calls.** Calling `run_sweep` again with the same profile while a sweep is running rejoins that job instead of starting a second scrape.
- **Default profile.** When `profile_path` is omitted, the sweep uses the last saved profile, then the newest profile in `profiles/`, then `profiles/custom_profile.yaml`, `profiles/paralegal_nyc.yaml`, and `config.sample.yaml`. A profile saved by `create_profile` becomes the last saved profile.
- **Previously seen postings.** The sweep skips postings recorded in an earlier run and reports `previously_seen_count` and `new_count`. Pass `include_seen=true`, or set `history.enabled: false` in the profile, to report every posting.

Every MCP sweep enables a timestamped debug log and returns its path in `debug_log`. The log records the pipeline stages and source diagnostics without writing to the MCP stdout stream.
Each sweep log also records its execution method as `wizard`, `cli`, or `mcp`.

Enabled engines run concurrently behind one adapter, so the sweep takes about as long as the slowest engine. A single engine that times out or fails does not fail the call; report `skipped_sources` to the user when it comes back non-empty, naming the engine and the reason (`timeout`, `circuit_open`, or the error text).

When `create_profile` receives no `sources_config`, it enables the built-in engines
and every installed optional engine whose default configuration passes preflight.
It returns `enabled_engines` and `engines_not_enabled` so you can tell the user what
will run and what needs setup. OpenRoles only reads named company boards, so the
interactive wizard can skip it when the user leaves company slugs blank. Apify can incur charges,
so never enable or run it without the user's explicit opt-in. Do not pause a routine
search to ask the user to choose from all engines; ask only when the user requests an
engine that needs setup, paid-service consent, or a search constraint.

If the user supplies `sources_config`, preserve that selection rather than adding
other engines. Do not install optional packages automatically. Mention optional
engines that need installation or configuration when the user asks to use every
engine.

### 3. `get_sweep_status`
Reports on, or waits for, a sweep started by `run_sweep`. It also applies the finished sweep's cards to the live session, so `get_jobs`, `submit_judgments`, and `render_report` work right after it reports `completed`.

- **When to call.** Whenever `run_sweep` returns `sweep_status: "running"`. Repeat until it returns `sweep_status: "completed"`, then inspect the roles with `get_jobs`.
- **Key parameters**:
  - `job_id`: job id returned by `run_sweep`. Defaults to the most recent sweep job.
  - `wait_seconds`: longest time to block before returning progress (default `45`, clamped to `0..600`).
- **Response.** `sweep_status` reads `running`, `completed`, or `failed`. A running job also reports `progress` (`step`, `total`, `label`) and `elapsed_seconds`; a completed job reports the same summary fields as `run_sweep`.

### 4. `get_results`
Retrieves top matching roles, playbook recommendations, and artifact paths from a completed sweep without re-running discovery.

- **When to call.** Call when the user asks for matches, summaries, top roles, or playbook recommendations after a sweep.
- **Key parameters**:
  - `profile_stem`: profile stem identifier (such as `"pedro_writer"`). If omitted, finds the latest result JSON in the directory.
  - `results_dir`: directory containing result JSON files. Defaults to `"results"`.
  - `limit`: number of top roles to return. Defaults to `10`.

### 5. `export_report`
Rebuilds PDF, PNG, CSV, or JSON artifacts from existing sweep results without re-running discovery or scoring.

- **When to call.** Call when the user requests a regenerated PDF or exported CSV. Also call when the user specifies a custom destination directory.
- **Key parameters**:
  - `json_source`: optional direct path to a specific sweep result JSON file.
  - `profile_stem`: optional stem name to locate the latest sweep JSON.
  - `formats`: list of formats to export. Defaults to `["pdf"]`. Can include `"pdf"`, `"csv"`, `"json"`, or `"png"`. PNG rasterizes the report PDF, so requesting it also writes the PDF.
  - `candidate_name`: name to render in the header of the regenerated PDF. Defaults to `"Job Seeker"`.
  - `output_dir`: optional target output folder. If omitted, writes to `results/`.
  - `job_tracking`: optional override for the profile's `export.tracking` setting on a CSV export. Leave unset to follow the profile.

### 6. `get_jobs`
Returns the card records held in the current sweep session, ranked by match.

- **When to call.** After `run_sweep`, to inspect the deterministic card records before supplying judgment.
- **Key parameters**:
  - `profile_stem`: optional profile identifier to load a persisted session from disk.
  - `results_dir`: directory holding `report_session.json`. Defaults to `"results"`.
  - `limit`: optional number of cards to return (omit to return all).

### 7. `submit_judgments`
Overrides a job's deterministic card fields with LLM-supplied judgment.

- **When to call.** After reviewing `get_jobs`, to supply your own `match_pct`, `resume_track`,
  `domain`, `summary`, `requirements`, `alignment`, or `has_extended_response`.
- **Key parameters**:
  - `job_id`: stable job id returned by `run_sweep` or `get_jobs`.
  - `match_pct`: LLM-assessed match percentage (0-100). Set this only after independently comparing the candidate's resume and preferences with available job evidence. Do not reuse the deterministic keyword-overlap score. Supplying it flips the report label from `KEYWORD OVERLAP` to `MATCH` for that card.
  - `resume_track`, `resume_color`, `domain`, `summary`, `requirements`, `alignment`,
    `has_extended_response`, `app_format`, `comp`, `benefits`, `page_theme`: optional overrides.
    Sweepy merges only non-null fields.

### 8. `import_jobs`
Appends agent-found jobs (canonical card schema) into the current session.

- **When to call.** When your web search found roles the deterministic scrapers missed.
- **Key parameters**:
  - `jobs_json`: a JSON string encoding a list of card records.
  - `validate`: optional. Set it to `true` to run URL validation before importing (default `false`, because the agent already vetted the links).

### 9. `render_report`
Renders the cards PDF from the current session, writing through the sandbox.

- **When to call.** After `submit_judgments` and/or `import_jobs`, to produce the final report.
- **Key parameters**:
  - `profile_stem`: optional profile identifier to load a persisted session from disk.
  - `results_dir`: results directory. Defaults to `"results"`.
  - `output_filename`: optional explicit output PDF path (must stay inside the workspace).
  - `playbook`: optional plain-text strategy note. Sweepy escapes ampersands and angle brackets, converts newlines to line breaks, and renders `**bold**`. The note is saved with the session, so a later call without it reuses the saved text. Empty with nothing saved generates a deterministic playbook.

Returns `pdf_report`, `pages`, `card_count`, and `playbook_saved`.

### 10. `convert_document`
Converts any supported document to PDF.

- **When to call.** When the user hands you a résumé, notes file, or other document that isn't a PDF and wants a PDF copy. `create_profile` needs a PDF input.
- **Key parameters**:
  - `document_path`: absolute or relative path to the `.docx`, `.doc`, `.txt`, `.md`, or `.pdf` file.
  - `pdf_path`: optional output PDF path. Blank saves the PDF next to the source file.
- **Behavior.** DOCX files rebuild through `python-docx` + `reportlab`, with a `docx2pdf` fallback when Microsoft Word is available. Legacy `.doc` files need Word. Text and Markdown render with headings and bullets, and `.pdf` sources pass through untouched. The output must stay inside the workspace sandbox unless you set `SWEEPY_ALLOW_EXTERNAL_WRITES`.

### 11. `convert_docx`
Converts a `.docx` file to PDF and nothing else.

- **When to call.** When you know the file is a DOCX and want the Word-aware path. Prefer `convert_document` for any other extension.
- **Key parameters**:
  - `docx_path`: absolute or relative path to the `.docx` file.
  - `pdf_path`: optional output PDF path. Blank saves the PDF next to the DOCX.
- **Behavior.** Uses `python-docx` + `reportlab` first, then falls back to `docx2pdf` when Microsoft Word is available. The output must stay inside the workspace sandbox unless you set `SWEEPY_ALLOW_EXTERNAL_WRITES`.

### 12. `clear_history`
Forgets the postings Sweepy already reported so the next sweep can report them again.

- **When to call.** When the user asks to see roles from earlier sweeps again, or wants to start a fresh search cycle.
- **Key parameters**:
  - `profile_path`: optional path to the profile YAML.
  - `profile_stem`: optional profile identifier, such as `pedro_writer`. With neither argument, the tool clears the profile used by the last sweep.
- **Response.** Returns the cleared `scope`, the number of postings removed, and how many remain.

---

## User interaction workflow

Follow this conversational sequence when assisting users:

### Discover preferences
If the user doesn't have a profile, ask for:
- Target job titles
- Location preference (remote, hybrid, or specific city)
- Path to their résumé PDF or DOCX file
- Any salary floor or must-have skill keywords

Don't require every optional field before proceeding; sensible defaults exist for salary (`0`), platforms, and hybrid preferences.

### Build the profile
Call `create_profile`. Tell the user where Sweepy saved the configuration file, and cite its path.

### Execute and assess the sweep
Call `run_sweep` with the profile path. Note to the user that live board scraping and uptime verification take a few minutes. Explain that its initial scores reflect keyword overlap only, not model judgment.

When the response reads `sweep_status: "running"`, call `get_sweep_status` with the returned `job_id` and repeat until it reads `completed`. Report the step label while you wait so the user sees progress instead of a stalled request.

For the default workflow, call `get_jobs` and inspect the available details for the roles. Compare each assessable role with the candidate's resume and preferences, then call `submit_judgments` with an independently determined `match_pct` and evidence-grounded summary, requirements, and alignment. Assess all relevant cards returned by `get_jobs`; do not copy keyword scores or fabricate missing details. If evidence is insufficient, say so and retain the keyword-overlap label for those roles. Call `render_report` after submitting judgments.

Send the whole assessment as one `judgments` list, with a `job_id` and `match_pct` per entry, so 24 roles cost one call instead of 24. `run_sweep` reports `assessment_mode` and `assessed_count`; the default `agent` mode makes `render_report` refuse a mixed report and return the unassessed job ids. `report.assessment: keyword` restores keyword-only reports, and `SWEEPY_REQUIRE_JUDGMENTS=1` extends the gate to every profile and to `export_report`.

Use deterministic scores without LLM judgment only when the user specifically asks for keyword-only results or the role evidence is insufficient for responsible judgment.

### Present matches
Format match results using markdown tables and structured lists:
- Display model-assessed scores as `NN% MATCH` only after submitting LLM judgments. Label unassessed scores `NN% KEYWORD OVERLAP`; never imply that calling the MCP by itself creates LLM matches.
- Provide active Markdown links to each live job posting.
- Show company name, location, and workplace model (Remote, Hybrid, On-site).
- Include posted salary ranges when detected.
- Highlight candidate strengths and résumé keywords that triggered the match.
- Surface strategic playbook recommendations (such as recommended portfolio samples or talking points).

### Export on demand
Offer to generate custom exports or regenerate the styled PDF report if the user requests saving files to specific directories.

---

## Environment and CLI fallback
When operating in environments without direct MCP tool support:

### Execution command
Run the primary orchestrator from the repository root:

```bash
python swee.py --profile profiles/your_profile.yaml
```

After one editable install (`pip install -e .`), the `sweepy` console script runs the same entry point, so `sweepy --profile profiles/your_profile.yaml` works from the repository root. The `python swee.py` form always works, installed or not.

To run interactively with the terminal wizard:

```bash
python swee.py
```

The wizard opens its main menu. There you run a sweep with the loaded profile, create or load a saved profile, edit a profile, toggle debug logging, adjust scoring and scaling, manage aggregators, manage or download job engines, convert a document to PDF (the bonus entry accepts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf` with no profile loaded), and update Sweepy. `python swee.py --setup` opens the same menu, and `python swee.py --setup --profile profiles/your_profile.yaml` opens that profile for editing straight away.

The launchpad shows six tiles:

- **Launch Sweep**: run your job search now
- **Build Profile**: set up your job search
- **Load Profile**: open a search you saved
- **Sweep Settings**: change ranking, cards, and history
- **Sweepy's Toolbox**: profile edits, logs, and help
- **Exit Sweepy**: save changes and close

Every submenu starts with **← Back** and returns to the menu that opened it. Esc goes up one level: from a question to the previous answer, from a submenu to its parent, and from the launchpad out of the wizard. Ctrl+C quits from anywhere.

List the job engines and their install state, or download the optional ones:

```bash
python swee.py --list-engines
python swee.py --install-engines all
python swee.py --install-engines jobdrop --allow-engine-conflicts
```

`pip install -e ".[all-engines]"` installs HireHunt, openroles, and Apify in one resolution. `jobdrop` stays out because its `curl-cffi` pin cannot resolve alongside JobSpy. Install it separately with the explicit conflict override:

```bash
python swee.py --install-engines jobdrop --allow-engine-conflicts
```

Build a profile without prompts when the environment has no interactive terminal:

```bash
python swee.py --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,ats
```

Run a sweep with the last saved profile:

```bash
python swee.py --run
```

The wizard writes the last saved profile to `profiles/.last_profile`. When that file is missing, `--run` picks the newest profile in `profiles/`, then falls back to `profiles/custom_profile.yaml`, `profiles/paralegal_nyc.yaml`, and `config.sample.yaml`.

Update the installed checkout with `python swee.py --update` (pull the latest code
and reinstall dependencies). `python swee.py --check-update` reports whether a newer
version exists without changing anything. The update refuses to run when the checkout
holds uncommitted changes.

Enable CLI debug logging with `--debug` (writes timestamped rotating logs under `logs/`;
show the latest entries with `python swee.py --logs`). Set `debug: true` in a
profile or `SWEEPY_DEBUG=1` in the environment to enable it without the flag. MCP
`run_sweep` calls always write a debug log and return its path.

Convert any supported document to PDF beside the original file, with no prompts:

```bash
python swee.py --convert path/to/resume.docx
```

`--convert` accepts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf`. It prints the final
PDF path and exits with code `1` when the file is missing or unsupported.

### Running the MCP server manually
Start the stdio server directly:

```bash
python server.py
```

### Python dependencies
Install Sweepy and its pinned core dependencies from the repository root:

```bash
pip install -e .
```

The compatible optional engines install with `pip install -e ".[all-engines]"` or `python swee.py --install-engines all`:
- `hirehunt` (India-first boards, plus LinkedIn and Indeed APIs)
- `openroles` (Greenhouse, Lever, Ashby, and Workday boards)
- `apify-client` (`apify` engine; needs `APIFY_TOKEN`)

`jobdrop` installs separately because its dependency metadata conflicts with JobSpy:

```bash
python swee.py --install-engines jobdrop --allow-engine-conflicts
```

Sweepy skips an engine whose library is missing and reports it in `skipped_sources`, so a missing extra never breaks a sweep.
