# Sweepy agent guidelines

Guidelines for AI assistants (such as Antigravity, Claude, and Cursor) interacting with the Sweepy job search engine.

## Overview

Sweepy discovers, filters, scores, and exports job postings from Applicant Tracking Systems (Greenhouse, Ashby, Lever, Workable) and aggregators.

AI assistants can interact with Sweepy through:
1. **MCP tools** via `server.py` (`stdio` transport).
2. **Direct commands** via `swee.py`.

---

## Tool reference and sequencing

Sweepy exposes MCP tools through `server.py` in two workflows: a one-shot flow and a
hybrid stateful flow that lets your LLM supply its own judgment.

**One-shot (no LLM judgment):**

```text
create_profile → run_sweep → get_results → export_report (optional)
```

**Hybrid stateful (LLM judgment through MCP):**

```text
run_sweep → get_jobs → submit_judgments → render_report
```

### 1. `create_profile`
Builds and saves a YAML configuration profile in the `profiles/` directory.

- **When to call.** Call when the user names target job roles, a preferred location, or a résumé path. Call it again to update search preferences.
- **Key parameters**:
  - `name`: candidate's full name.
  - `titles`: list of job titles to search for (such as `["Technical Writer", "Documentation Engineer"]`).
  - `location`: target city, state, or metro area (such as `"New York, NY"`).
  - `resume_path`: path to the candidate PDF résumé (absolute or relative).
  - `remote_only`: set `True` if the candidate accepts only remote roles. Defaults to `False`.
  - `include_hybrid`: set `True` to include hybrid roles alongside remote or on-site roles. Defaults to `True`.
  - `min_salary`: lowest acceptable base salary as an integer (such as `90000`). Use `0` if unconstrained.
  - `must_have_skills`: optional list of mandatory keywords to boost ranking (such as `["API Documentation", "Markdown"]`).
  - `platforms`: optional dictionary enabling or disabling scrapers (such as `{"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}`).
  - `output_filename`: optional explicit destination YAML path. Defaults to `profiles/{name}_{title}.yaml`.

### 2. `run_sweep`
Executes the 5-stage discovery pipeline: discovery, validation, scoring, report generation, and CSV/JSON export. It populates the session with deterministic cards and returns their ids.

### 3. `get_results`
Retrieves top matching roles, playbook recommendations, and artifact paths from a completed sweep without re-running discovery.

- **When to call.** Call when the user asks for matches, summaries, top roles, or playbook recommendations after a sweep.
- **Key parameters**:
  - `profile_stem`: profile stem identifier (such as `"pedro_writer"`). If omitted, finds the latest result JSON in the directory.
  - `results_dir`: directory containing result JSON files. Defaults to `"results"`.
  - `limit`: number of top roles to return. Defaults to `10`.

### 4. `export_report`
Rebuilds PDF, PNG, CSV, or JSON artifacts from existing sweep results without re-running discovery or scoring.

- **When to call.** Call when the user requests a regenerated PDF or exported CSV. Also call when the user specifies a custom destination directory.
- **Key parameters**:
  - `json_source`: optional direct path to a specific sweep result JSON file.
  - `profile_stem`: optional stem name to locate the latest sweep JSON.
  - `formats`: list of formats to export. Defaults to `["pdf"]`. Can include `"pdf"`, `"csv"`, `"json"`, or `"png"`. PNG rasterizes the report PDF, so requesting it also writes the PDF.
  - `candidate_name`: name to render in the header of the regenerated PDF. Defaults to `"Job Seeker"`.
  - `output_dir`: optional target output folder. If omitted, writes to `results/`.

### 5. `get_jobs`
Returns the card records held in the current sweep session, ranked by match.

- **When to call.** After `run_sweep`, to inspect the deterministic card records before supplying judgment.
- **Key parameters**:
  - `profile_stem`: optional profile identifier to load a persisted session from disk.
  - `results_dir`: directory holding `report_session.json`. Defaults to `"results"`.
  - `limit`: optional number of cards to return (omit to return all).

### 6. `submit_judgments`
Overrides a job's deterministic card fields with LLM-supplied judgment.

- **When to call.** After reviewing `get_jobs`, to supply your own `match_pct`, `resume_track`,
  `domain`, `summary`, `requirements`, `alignment`, or `has_extended_response`.
- **Key parameters**:
  - `job_id`: stable job id returned by `run_sweep` or `get_jobs`.
  - `match_pct`: optional LLM match percentage (0-100). Supplying it flips the report label from
    `KEYWORD OVERLAP` to `MATCH` for that card.
  - `resume_track`, `resume_color`, `domain`, `summary`, `requirements`, `alignment`,
    `has_extended_response`, `app_format`, `comp`, `benefits`, `page_theme`: optional overrides.
    Sweepy merges only non-null fields.

### 7. `import_jobs`
Appends agent-found jobs (canonical card schema) into the current session.

- **When to call.** When your web search found roles the deterministic scrapers missed.
- **Key parameters**:
  - `jobs_json`: a JSON string encoding a list of card records.
  - `validate`: optional. Set it to `true` to run URL validation before importing (default `false`, because the agent already vetted the links).

### 8. `render_report`
Renders the cards PDF from the current session, writing through the sandbox.

- **When to call.** After `submit_judgments` and/or `import_jobs`, to produce the final report.
- **Key parameters**:
  - `profile_stem`: optional profile identifier to load a persisted session from disk.
  - `results_dir`: results directory. Defaults to `"results"`.
  - `output_filename`: optional explicit output PDF path (must stay inside the workspace).
  - `playbook`: optional playbook text. When empty, Sweepy generates a deterministic playbook.

### 9. `convert_docx`
Converts a `.docx` file to PDF.

- **When to call.** When the user hands you a Word résumé instead of a PDF. `create_profile` requires a PDF, so convert the DOCX first.
- **Key parameters**:
  - `docx_path`: absolute or relative path to the `.docx` file.
  - `pdf_path`: optional output PDF path. Blank saves the PDF next to the DOCX.
- **Behavior.** Uses `python-docx` + `reportlab` first, then falls back to `docx2pdf` when Microsoft Word is available. The output must stay inside the workspace sandbox unless you set `SWEEPY_ALLOW_EXTERNAL_WRITES`.

---

## User interaction workflow

Follow this conversational sequence when assisting users:

### Discover preferences
If the user doesn't have a profile, ask for:
- Target job titles
- Location preference (remote, hybrid, or specific city)
- Path to their résumé PDF
- Any salary floor or must-have skill keywords

Don't require every optional field before proceeding; sensible defaults exist for salary (`0`), platforms, and hybrid preferences.

### Build the profile
Call `create_profile`. Tell the user where Sweepy saved the configuration file, and cite its path.

### Execute the sweep
Call `run_sweep` with the profile path. Note to the user that live board scraping and uptime verification take a few moments.

### Present matches
Format match results using markdown tables and structured lists:
- Display the match score percentage prominently (such as `NN% MATCH`).
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

To run interactively with the terminal wizard:

```bash
python swee.py
```

Enable debug logging with `--debug` (writes rotating logs under `logs/`; show the
latest entries with `python swee.py --logs`). Set `debug: true` in a profile or
`SWEEPY_DEBUG=1` in the environment to enable it without the flag.

### Running the MCP server manually
Start the stdio server directly:

```bash
python server.py
```

### Python dependencies
Install the required dependencies:
- `mcp` (FastMCP server)
- `reportlab` (PDF generation)
- `pandas` (tabular processing and CSV export)
- `requests` (network requests and validation)
- `pyyaml` (profile configuration)
- `pymupdf` (PDF text extraction and PNG rasterization)
- `python-docx` (DOCX text extraction for the DOCX-to-PDF converter)
- `python-jobspy` (job board scraping)
- `beautifulsoup4` (HTML stripping for Greenhouse, Lever, and Workable descriptions)
- `questionary` (interactive wizard)
- `anyio` (async I/O for MCP)
