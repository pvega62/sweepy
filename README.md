# Sweepy

**Sweepy** is a free Python automation tool. It aggregates, de-duplicates, and scores job postings across multiple ATS platforms and job boards. It uses dynamic PDF résumé parsing to score matches. Finally, it generates structured datasets and a curated, card-per-page PDF report.

Sweepy works **with or without an LLM**. With no LLM key it produces a fully deterministic report. The report includes keyword-overlap scores, automatic resume-track routing, and extracted summaries. It labels them honestly as `NN% KEYWORD OVERLAP`. Connect your own LLM client through MCP to supply richer judgment, and Sweepy re-labels those cards `NN% MATCH`.

TL;DR: He's just a chill lil guy that **sweeps** the internet for job postings and scores them against your résumé.

## Features and architecture
- **Multi-platform scraping**: Uses `python-jobspy` to extract postings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter without API keys.
- **Deterministic ATS sources**: Fetches Ashby and Workable job boards and Built In NYC listings directly (no key) and normalizes them into one schema.
- **ATS discovery and classification**: Inspects URLs to classify direct ATS endpoints, such as Greenhouse, Ashby, Lever, or Workable, versus aggregator feeds.
- **Dynamic scoring**: Dynamically extracts text from your PDF résumé, computes a weighted overlap against the job description using `must_have_skills`, and identifies `missing_skills`.
- **Dual resume routing**: Route each job to the best of N named resume tracks by keyword overlap. The route renders as a color-coded `SUBMIT: ...` badge.
- **Application playbooks**: Each scored role includes a short `playbook` string — a tailored recommendation naming the résumé keywords to highlight in a cover letter, or a generic tailoring tip when nothing matches.
- **Heuristic tagging**: Uses regex pattern matching to flag postings requiring extended written responses, such as "cover letter" or "assessment," versus standard quick applies.
- **Link validation**: Executes live HTTP `GET` requests to prune expired links and detect platform-specific soft 404 redirects, for example, Ashby returning a blank state.
- **Reporting**: Generates an atomic, styled card PDF (the default) plus prioritized `.csv` and `.json` data dumps. The legacy table layout remains available via `report.style: legacy`.

## Prerequisites
- **Python 3.10+**
- **Note for Python 3.13 users:** The `pymupdf` package may require source compilation if pre-built wheels are not available yet. Ensure you have the Microsoft C++ Build Tools installed and select the "Desktop development with C++" workload before you install dependencies.

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -r requirements.txt
```

Verify your installation:
```bash
python swee.py --version
```

## Dependencies
- **pymupdf** — reads and extracts text from your résumé PDF.
- **python-jobspy** — scrapes job boards securely without requiring an API key.
- **reportlab** — generates the styled PDF report with clickable links.
- **requests** — sends web requests to check if URLs are still active.
- **pandas** — tabular processing for the CSV and JSON exports.
- **pyyaml & questionary** — handle the interactive configuration wizard.
- **mcp** and **anyio** — power the optional MCP server for AI assistant integration.

## Command-line usage

### 1. Interactive setup wizard
Use the built-in questionary command-line tool to generate a YAML configuration profile:
```bash
python swee.py --setup
```

### 2. Execution pipeline
Run Sweepy by passing a configuration profile. The engine executes a 5-stage pipeline:
1. **Profile loading**: Parses YAML and validates constraints.
2. **Discovery**: Executes scrapers across configured ATS platforms and aggregates postings.
3. **Validation**: Prunes dead links and parses soft 404 redirects.
4. **Scoring**: Parses the provided résumé PDF, calculates keyword overlap, and generates custom application playbooks.
5. **Generation**: Builds the date-stamped PDF, CSV, and JSON payloads.

```bash
python swee.py --profile profiles/your_custom_profile.yaml
```

## Configuration schema

You define profiles in YAML format and store them in the `profiles/` directory.

```yaml title="profiles/paralegal_nyc.yaml"
name: "Alex Rivera"

search:
  titles:
    - "Paralegal"
    - "Legal Assistant"
  location: "New York, NY"
  remote_only: false
  include_hybrid: true   # Set to false to exclude hybrid positions
  min_salary: 65000

resume:
  path: "C:/absolute/path/to/resume.pdf"
  must_have_skills:
    - "Westlaw"
    - "LexisNexis"
    - "Contract Review"
  keywords_weight: 1.5
  # Optional dual-targeting: route each job to the best track by keyword overlap.
  tracks:
    - name: "Tech Writer Resume"
      path: "C:/path/to/tech_writer.pdf"
      color: "#1D4ED8"
      route_keywords: ["api", "docs-as-code", "developer"]
    - name: "UX Writer Resume"
      path: "C:/path/to/ux_writer.pdf"
      color: "#7E22CE"
      route_keywords: ["ux", "content design", "microcopy"]

platforms:
  greenhouse: true
  ashby: true
  lever: true
  workable: true
  aggregators: false
  # Custom platforms or ATS domains:
  custom:
    - name: "SmartRecruiters"
      domain: "smartrecruiters.com"
      enabled: true
    - name: "Breezy HR"
      domain: "breezy.hr"
      enabled: true

# Deterministic (no-key) sources. Empty lists fall back to data/sources/*.txt seeds.
sources:
  jobspy:
    linkedin: true
    indeed: true
    glassdoor: true
    zip_recruiter: true
  ashby:
    orgs: []            # e.g. ["modal", "camunda"]
  workable:
    slugs: []           # e.g. ["soda-data-nv", "reversinglabs"]
  builtinnyc:
    enabled: true
    categories: []      # e.g. ["jobs/technical-writer"]

report:
  style: "cards"        # "cards" (default) | "legacy"
  cards_per_page: 4
  max_cards: 24         # 0 = unlimited
  destinations: []      # extra directories to copy the PDF into

export:
  format: "pdf,csv,json"
  output_dir: "results"
```

## Custom platforms and caveats

Register custom ATS domains under `platforms.custom` to classify postings directly into your report directory.

### Platform compatibility

| Platform type | Examples | Compatibility | Caveats |
| :--- | :--- | :--- | :--- |
| **Public ATS** | Greenhouse, Ashby, Lever, Workable, SmartRecruiters, Breezy HR | **Fully supported** | Standard server-rendered job pages parse and validate cleanly. |
| **Client-rendered SPAs** | Workday (`myworkdayjobs.com`), Oracle HCM | **Limited** | Platforms require dynamic JavaScript. Without a browser grid, initial HTML payloads may lack descriptions. |
| **Auth-walled portals** | Handshake, corporate intranets | **Unsupported** | Require session cookies or SSO credentials. |
| **Anti-bot aggregators** | Boards with Cloudflare Turnstile or PerimeterX | **Rate-limited** | Automated HTTP requests may trigger HTTP 403 blocks without proxy rotation. |

## Model Context Protocol integration

Sweepy provides a built-in MCP server (`server.py`) using `stdio` transport. This integration enables AI assistants, such as Antigravity and Claude Desktop, to configure search profiles, run sweeps, and analyze candidate matches directly through conversational prompts.

### Available tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `create_profile` | `name`, `titles`, `location`, `resume_path`, `remote_only` *(default `false`)*, `include_hybrid` *(default `true`)*, `min_salary` *(default `0`)*, `must_have_skills`, `platforms`, `output_filename` | Generates a validated YAML search profile without running the terminal wizard. |
| `run_sweep` | `profile_path` *(optional)* | Runs the sweep pipeline, populates the session with deterministic cards, and returns their ids. |
| `get_jobs` | `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `limit` *(optional)* | Returns the card records held in the current session. |
| `submit_judgments` | `job_id`, `match_pct` *(optional)*, `resume_track`, `resume_color`, `domain`, `summary`, `requirements`, `alignment`, `has_extended_response`, `app_format`, `comp`, `benefits`, `page_theme` | Overrides a card's deterministic fields with LLM judgment; supplying `match_pct` flips the label to `MATCH`. |
| `import_jobs` | `jobs_json`, `validate` *(default `false`)* | Appends agent-found jobs (canonical card schema) into the session. |
| `render_report` | `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `output_filename` *(optional)*, `playbook` *(optional)* | Renders the cards PDF from the session. |
| `get_results` | `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `limit` *(default `10`)* | Retrieves the top matching roles, playbook recommendations, and artifact paths from the most recent run. |
| `export_report` | `json_source` *(optional)*, `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `formats` *(default `['pdf']`)*, `candidate_name` *(default `'Job Seeker'`)*, `output_dir` *(optional)* | Regenerates a PDF, CSV, or JSON report from an existing sweep result without re-running discovery or scoring. |

The hybrid stateful flow is `run_sweep → get_jobs → submit_judgments → render_report`. With no LLM
at all, `run_sweep` alone still renders the full cards PDF from deterministic fields.

### Connecting to Antigravity or Claude Desktop

Add Sweepy to your local client's MCP configuration file (for example, `mcp_config.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sweepy": {
      "command": "python",
      "args": [
        "/path/to/sweepy/server.py"
      ]
    }
  }
}
```

Once registered, your AI assistant can run commands such as:
- *"Create a Sweepy profile for Alex searching for remote Technical Writer roles in New York. The résumé is at `path/to/resume.pdf`."*
- *"Run a sweep with the writer profile and show the top 5 matches."*
- *"Regenerate the PDF from the last pedro_writer sweep and save it to the Desktop."*

For detailed LLM prompting patterns, tool sequencing, and workflows, consult [AGENTS.md](AGENTS.md).

## Sample report

Sweepy produces a card-style PDF report. A redacted example:

- [Sample report (PDF)](docs/sample_report.pdf)
- [Sample report, page 1 (PNG)](docs/sample_report.png)

## Legal and responsible use

Sweepy uses `python-jobspy` to scrape public job boards including LinkedIn, Indeed, Glassdoor, and ZipRecruiter without API keys. It also fetches the public Ashby and Workable job-board APIs plus Built In NYC pages directly. Scraping may violate the Terms of Service of some platforms. You are responsible for how you use this tool.

- This project is intended for **personal job searching**, not bulk data collection or redistribution.
- Respect rate limits and the target sites' policies. Do not hammer endpoints. Sweepy sends a polite User-Agent and a small inter-request delay (override with the `SWEEPY_SOURCE_DELAY` environment variable).
- Sweepy doesn't provide legal advice. Review the ToS of any platform you query before relying on it.

See [`python-jobspy`](https://github.com/Bunsly/JobSpy) for the upstream scraper and its own usage notes.

## Module reference
- `swee.py`: Primary orchestrator and `argparse` command-line entry point.
- `server.py`: Model Context Protocol (`stdio`) server exposing tools for large language model (LLM) automation.
- `engine/config.py`: Interactive command-line wizard and YAML parsing logic.
- `engine/discovery.py`: Scraper orchestration (jobspy + deterministic sources), ATS detection, and deduplication.
- `engine/sources/`: Deterministic Ashby, Workable, and Built In NYC fetchers with seed lists in `data/sources/`.
- `engine/validator.py`: URL uptime checking and HTTP soft 404 detection.
- `engine/scorer.py`: Resume keyword extraction, percentage matching, and tagging.
- `engine/enrich.py`: Deterministic card enrichment—summaries, requirements, comp, resume-track routing, and match provenance.
- `engine/session.py`: Thread-safe card-record store backing the MCP hybrid stateful flow.
- `engine/report.py`: The default card-layout PDF renderer (faithful port of the reference layout).
- `engine/pdf_builder.py`: The legacy table-layout PDF renderer (`report.style: legacy`).
- `engine/exporter.py`: CSV and JSON export.

## License

Sweepy is released under the [MIT License](LICENSE).
