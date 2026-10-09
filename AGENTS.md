# Sweepy agent guidelines

Guidelines for AI assistants (such as Antigravity, Claude, and Cursor) interacting with the Sweepy job search engine.

## Overview

Sweepy discovers, filters, scores, and exports job postings from Applicant Tracking Systems (Greenhouse, Ashby, Lever, Workable) and aggregators.

AI assistants can interact with Sweepy through:
1. **MCP tools** via `server.py` (`stdio` transport).
2. **Direct commands** via `swee.py`.

---

## Tool reference and sequencing

Sweepy exposes four MCP tools through `server.py`:

```
create_profile ──► run_sweep ──► get_results ──► export_report (optional)
```

### 1. `create_profile`
Builds and saves a YAML configuration profile in the `profiles/` directory.

- **When to call**: Call when the user specifies target job roles, preferred location, or a résumé path, or asks to update search preferences.
- **Key parameters**:
  - `name`: Candidate's full name.
  - `titles`: List of search target job titles (for example, `["Technical Writer", "Documentation Engineer"]`).
  - `location`: Target city, state, or metro area (for example, `"New York, NY"`).
  - `resume_path`: Path to candidate PDF résumé (can be absolute or relative).
  - `remote_only`: Set `True` if candidate exclusively accepts remote roles. Defaults to `False`.
  - `include_hybrid`: Set `True` to include hybrid roles alongside remote or on-site roles. Defaults to `True`.
  - `min_salary`: Minimum acceptable base salary integer (for example, `90000`). Use `0` if unconstrained.
  - `must_have_skills`: Optional list of mandatory keywords to boost ranking (for example, `["API Documentation", "Markdown"]`).
  - `platforms`: Optional dictionary enabling or disabling scrapers (for example, `{"greenhouse": True, "ashby": True, "lever": True, "workable": True, "aggregators": False}`).
  - `output_filename`: Optional explicit destination YAML path. Defaults to `profiles/{name}_{title}.yaml`.

### 2. `run_sweep`
Executes the five-stage discovery pipeline: discovery, validation, scoring, report generation, and CSV/JSON export.

- **When to call**: Call when the user asks to run a job search or execute a sweep.
- **Key parameters**:
  - `profile_path`: Optional path to the YAML profile. If omitted, Sweepy automatically selects the most recently created or modified profile in `profiles/`.

### 3. `get_results`
Retrieves top matching roles, playbook recommendations, and artifact paths from a completed sweep without re-running scraping.

- **When to call**: Call when the user asks for matches, summaries, top roles, or playbook recommendations after a sweep.
- **Key parameters**:
  - `profile_stem`: Profile stem identifier (for example, `"pedro_writer"`). If omitted, finds the latest result JSON in the directory.
  - `results_dir`: Directory containing result JSON files. Defaults to `"results"`.
  - `limit`: Number of top roles to return. Defaults to `10`.

### 4. `export_report`
Rebuilds PDF, CSV, or JSON artifacts from existing sweep results without re-running network scraping or scoring.

- **When to call**: Call when the user requests a regenerated PDF or exported CSV. Also call when the user specifies a custom destination directory.
- **Key parameters**:
  - `json_source`: Optional direct path to a specific sweep result JSON file.
  - `profile_stem`: Optional stem name to locate the latest sweep JSON.
  - `formats`: List of formats to export. Defaults to `["pdf"]`. Can include `"pdf"`, `"csv"`, `"json"`.
  - `candidate_name`: Name to render in the header of the regenerated PDF. Defaults to `"Job Seeker"`.
  - `output_dir`: Optional target output folder. If omitted, writes to `results/`.

---

## User Interaction Workflow

Follow this conversational sequence when assisting users:

### Step 1: Discover Preferences
If the user doesn't have a profile, ask for:
- Target job titles
- Location preference (remote, hybrid, or specific city)
- Path to their résumé PDF
- Any minimum salary floor or must-have skill keywords

Don't require every optional field before proceeding; sensible defaults exist for salary (`0`), platforms, and hybrid preferences.

### Step 2: Build the Profile
Call `create_profile`. Inform the user that the configuration file is saved and cite its path.

### Step 3: Execute the Sweep
Call `run_sweep` with the profile path. Note to the user that live board scraping and uptime verification take a few moments.

### Step 4: Present Matches
Format match results using markdown tables and structured lists:
- Display the match score percentage prominently (for example, `92% Match`).
- Provide active markdown links to each live application posting.
- Show company name, location, and workplace model (Remote, Hybrid, On-site).
- Include posted salary ranges when detected.
- Highlight candidate strengths and resume keywords that triggered the match.
- Surface strategic playbook recommendations (for example, recommended portfolio samples or talking points).

### Step 5: Export on Demand
Offer to generate custom exports or regenerate the styled PDF report if the user requests saving files to specific directories.

---

## Environment and CLI Fallback

When operating in environments without direct MCP tool support:

### Execution Command
Run the primary orchestrator from the repository root:

```bash
python swee.py --profile profiles/your_profile.yaml
```

To run interactively with the terminal wizard:

```bash
python swee.py
```

### Running the MCP Server Manually
Start the stdio server directly:

```bash
python server.py
```

### Python Dependencies
Ensure required dependencies are installed:
- `mcp` (FastMCP server)
- `reportlab` (PDF generation)
- `pandas` (tabular processing and CSV export)
- `beautifulsoup4` (HTML parsing)
- `requests` (network requests and validation)
- `pyyaml` (profile configuration)
- `pypdf` / `pymupdf` (résumé text extraction)
