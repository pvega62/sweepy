# Sweepy

**Sweepy** is a free Python automation tool. It aggregates, de-duplicates, and scores job postings across multiple ATS (Applicant Tracking System) platforms and job boards. It uses dynamic PDF résumé parsing to score matches and generates structured datasets with a curated, card-per-page PDF report.

Sweepy works **with or without a Large Language Model (LLM)**. Without an LLM key it produces a fully deterministic report. The report includes keyword-overlap scores, automatic resume-track routing, and extracted summaries. It labels them as `NN% KEYWORD OVERLAP`. Connect your own LLM client through the Model Context Protocol (MCP) to supply richer judgment, and Sweepy re-labels those cards `NN% MATCH`.

TL;DR: A friendly tool that **sweeps** the internet for job postings and scores them against your résumé.

## Table of contents
- [Features and architecture](#features-and-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Command-line usage](#command-line-usage)
- [Resume formatting tips](#resume-formatting-tips)
- [Configuration schema](#configuration-schema)
- [Customizing sources for your field](#customizing-sources-for-your-field)
- [Default sources and how they run](#default-sources-and-how-they-run)
- [Custom platforms and caveats](#custom-platforms-and-caveats)
- [Model context protocol (MCP) integration](#model-context-protocol-mcp-integration)
- [Sample report](#sample-report)
- [Legal and responsible use](#legal-and-responsible-use)
- [Module reference](#module-reference)
- [License](#license)

## Features and architecture
- **Multi-platform scraping**: Uses `python-jobspy` to extract postings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter without API keys.
- **Deterministic ATS sources**: Fetches Greenhouse and Lever job boards, Ashby and Workable accounts, and Built In NYC listings directly without a key. It normalizes them into one schema.
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
- **pymupdf**—reads and extracts text from your résumé PDF and rasterizes the PNG report exports.
- **python-jobspy**—scrapes job boards securely without requiring an API key.
- **beautifulsoup4**—parses HTML for the Greenhouse, Lever, Workable, and Built In NYC sources.
- **reportlab**—generates the styled PDF report with clickable links.
- **requests**—sends web requests to check if URLs are still active.
- **pandas**—tabular processing for the CSV and JSON exports.
- **pyyaml & questionary**—handle the interactive configuration wizard.
- **mcp** and **anyio**—power the optional MCP server for AI assistant integration.

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
5. **Generation**: Builds the date-stamped PDF, CSV, and JSON payloads, plus PNG page images when `png` is in the export format.

```bash
python swee.py --profile profiles/your_custom_profile.yaml
```

## Resume formatting tips

Sweepy reads the PDF at `resume.path` and extracts its text. Clean, extractable text produces accurate match scores. The formatting that works for applicant tracking systems (ATS) also works for Sweepy.

### What Sweepy can't read

- **Non-PDF files.** Point `resume.path` at a PDF. The MCP `create_profile` tool rejects any other extension.
- **Scanned pages with no text layer.** Sweepy reads the text layer, not the page image. A scan or a photo of a résumé has no text layer, so scoring uses only `must_have_skills`. If that list is empty too, every role scores 75%.
- **Password-protected PDFs.** Sweepy can't open encrypted files.
- **Missing or corrupt files.** A bad path logs a warning and skips the extraction step. Only `must_have_skills` drives the score then.

> [!TIP]
> Run OCR on a scan first. It adds a text layer Sweepy can read.

### Formatting that breaks a sweep

- **Two or more columns.** Extractors read in order across the page, so columns interleave and scramble the text. ATS parsers often do the same.
- **Tables, text boxes, and sidebars.** Sweepy can read these out of order or merge them with neighbors.
- **Images, icons, and charts.** Extraction skips anything drawn as an image, and ATS parsers typically ignore it too.
- **Headers and footers.** Many parsers skip this region. Keep your name and contact details in the body.
- **Hyphenated line breaks.** A term split across lines (`e-` on one line, `discovery` on the next) breaks the whole-word keyword match.
- **Ligatures and decorative fonts.** `fi` and `fl` ligatures and unusual glyphs can extract as garbage.
- **Emoji and custom bullet glyphs.** These often drop or garble. Use a plain hyphen or a round bullet.

> [!TIP]
> Run the copy-paste test. Open the PDF, select all, and paste into a plain text editor. If the paste looks scrambled or empty, Sweepy sees the same.

### What applicant tracking systems prefer

Applicant tracking systems parse hundreds of résumés with the same kind of extraction Sweepy uses. Give them one clean text column.

- **One column, top to bottom.** Skip the two-column design with a sidebar.
- **Plain section headings.** Use `Experience`, `Education`, and `Skills`. Avoid tables and icons in headings.
- **Real text only.** No image-based headings, logos, or skill bars.
- **Standard fonts.** Arial, Calibri, Helvetica, or Times New Roman at 10-12pt.
- **Plain bullets and consistent dates.** Use one date format throughout, such as `Jan 2024 – Present`.
- **Reverse-chronological order.** Most recruiters and parsers expect it.
- **Contact info in the body.** ATS parsers often strip headers and footers.
- **Export from your word processor.** Save a PDF from your editor, and keep the `.docx` in case a portal requires it.
- **Mirror the job's wording.** If a posting says `e-discovery` or `docs-as-code`, use that exact term so keyword matching catches it.

### Keywords come from `must_have_skills`

Sweepy scores a role by counting how many of your keywords appear in the posting. The keyword list combines your profile's `must_have_skills` with a short built-in list of common tech and legal terms that Sweepy looks for in the résumé text.

The built-in list is small and generic, so most résumé terms never count on their own.

> [!TIP]
> Treat `must_have_skills` as your real keyword list. Pull terms from your résumé and from your industry, because Sweepy's built-in list is small and generic.

Add these to it:

- Every skill, tool, and platform you name in your résumé, such as `API Documentation`, `OpenAPI`, `Docusaurus`, `Figma`, or `Westlaw`.
- Terms your industry and target roles use, even when your résumé words them differently, such as `docs-as-code`, `e-discovery`, `content design`, or `prompt engineering`.
- Exact phrases from the postings you want. Sweepy matches whole words, so copy the posting's wording when it matters.

Keep these rules in mind:

- Matching ignores case and matches whole words. `e-discovery` doesn't match a posting that writes `ediscovery`, so add both spellings.
- Each keyword counts in the denominator. A long list lowers the score for roles that miss most of it, so keep the list to terms you have.
- `tracks[].route_keywords` is separate. It picks which résumé to send, and it never affects the match score.

```yaml
resume:
  path: "C:/path/to/your/resume.pdf"
  must_have_skills:
    - "API Documentation"
    - "OpenAPI"
    - "docs-as-code"
    - "Docusaurus"
    - "Content Design"
    - "Prompt Engineering"
```

## Configuration schema

You define profiles in YAML format and store them in the `profiles/` directory. Open a profile in any plain-text editor. Notepad works. VS Code or another IDE adds YAML syntax highlighting and validation if you want it. Indent with spaces, not tabs. YAML rejects tabs.

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
# Each source also honors its platforms.<x> flag (see "Default sources and how they run").
sources:
  jobspy:
    linkedin: true
    indeed: true
    glassdoor: true
    zip_recruiter: true
  greenhouse:
    enabled: true
    boards: []          # e.g. ["databricks", "gitlab", "cloudflare", "robinhood"]
  ashby:
    enabled: true
    orgs: []            # e.g. ["modal", "camunda"]
  lever:
    enabled: true
    companies: []       # e.g. ["leverdemo", "spotify"]
  workable:
    enabled: true
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
  format: "pdf,csv,json" # add "png" to also export page images
  output_dir: "results"
```

## Customizing sources for your field

Sweepy uses seed files in `data/sources/` as fallbacks when your profile leaves source lists empty. To target a specific field, add the relevant ATS boards, orgs, companies, slugs, and categories directly in your profile's `sources` section.

### Legal (example in `profiles/paralegal_nyc.yaml`)
```yaml
sources:
  ashby:
    orgs:
      - "crosby"
      - "normlaw"
      - "hargrove-firm"
      - "lawhive"
  workable:
    slugs:
      - "shegerianand-associates-1"
      - "harper-james"
      - "legalvision"
  builtinnyc:
    enabled: true
    categories:
      - "jobs/legal"
      - "jobs/legal/search/paralegal"
```

### Technical writing
```yaml
sources:
  greenhouse:
    enabled: true
    boards:
      - "gitlab"
      - "cloudflare"
  ashby:
    orgs:
      - "modal"
      - "perplexity"
      - "replit"
  lever:
    enabled: true
    companies:
      - "spotify"
  workable:
    slugs:
      - "soda-data-nv"
  builtinnyc:
    enabled: true
    categories:
      - "jobs/technical-writer"
```

### Healthcare/biotech
```yaml
sources:
  ashby:
    orgs:
      - "wealthsimple"
      - "ziina"
  workable:
    slugs:
      - "bask-health-1"
      - "atria-health"
  builtinnyc:
    enabled: true
    categories:
      - "jobs/healthcare"
```

### Adding custom platforms
Register additional ATS domains under `platforms.custom`:
```yaml
platforms:
  custom:
    - name: "LawCrossing"
      domain: "lawcrossing.com"
      enabled: true
    - name: "Indeed Legal"
      domain: "indeed.com/legal"
      enabled: true
```

**How it works.** Empty lists (`boards: []`, `orgs: []`, `companies: []`, `slugs: []`, `categories: []`) fall back to the curated seed files in `data/sources/`. Explicit lists in your profile override the seeds entirely (they replace, not merge). This lets you target exactly the companies and categories relevant to your search.

## Default sources and how they run

Out of the box, Sweepy sweeps five deterministic, key-free sources plus one aggregator path:

| Source | Config key | Seed file | Endpoint |
| :--- | :--- | :--- | :--- |
| Greenhouse | `sources.greenhouse.boards` | `data/sources/greenhouse_boards.txt` | `boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` |
| Ashby | `sources.ashby.orgs` | `data/sources/ashby_orgs.txt` | `api.ashbyhq.com/posting-api/job-board/{org}` |
| Lever | `sources.lever.companies` | `data/sources/lever_companies.txt` | `api.lever.co/v0/postings/{company}?mode=json` |
| Workable | `sources.workable.slugs` | `data/sources/workable_slugs.txt` | `apply.workable.com/api/v1/widget/accounts/{slug}` |
| Built In NYC | `sources.builtinnyc.categories` | `data/sources/builtin_categories.txt` | `builtinnyc.com/{category}` |
| Glassdoor | `sources.jobspy.glassdoor` | None | via `python-jobspy` |

### Gating rules

Each deterministic source runs only when both conditions hold:

1. Set `sources.<name>.enabled` to `true` (default).
2. Set `platforms.<name>` to `true` (default) where a matching key exists.

Built In NYC has no `platforms.builtinnyc` key, so it honors `sources.builtinnyc.enabled` alone. Glassdoor flows through `platforms.aggregators`, alongside the other `python-jobspy` sites.

> [!WARNING]
> Greenhouse and Lever now run by default, a change in v2.2.0. A profile that predates v2.2.0 discovers new postings unless you opt out. The flags `platforms.ashby: false`, `platforms.workable: false`, `platforms.greenhouse: false`, and `platforms.lever: false` now stop those deterministic seed sources. Before v2.2.0, they filtered only `python-jobspy` results. No flag default changed. Turn off a source with `sources.<name>.enabled: false` or its `platforms.<name>: false`.

### Bandwidth trade-off

Greenhouse boards fetch full content in one request per board (`?content=true`) so descriptions, departments, and pay metadata are present for scoring. Some boards return hundreds of postings, so a sweep can pull low tens of megabytes across all seeded boards. Sweepy pre-filters by your profile `titles` while normalizing to bound memory and time. It sends one request per source sequentially and applies the `SWEEPY_SOURCE_DELAY` delay (default 0.2 seconds) between requests. Smaller seed lists finish faster.

## Custom platforms and caveats

Register custom ATS domains under `platforms.custom` to classify postings directly into your report directory.

### Platform compatibility

| Platform type | Examples | Compatibility | Caveats |
| :--- | :--- | :--- | :--- |
| **Public ATS** | Greenhouse, Ashby, Lever, Workable, SmartRecruiters, Breezy HR | **Fully supported** | Standard server-rendered job pages parse and validate cleanly. |
| **Client-rendered SPAs** | Workday (`myworkdayjobs.com`), Oracle HCM | **Limited** | Platforms require dynamic JavaScript. Without a browser grid, initial HTML payloads may lack descriptions. |
| **Auth-walled portals** | Handshake, corporate intranets | **Unsupported** | Require session cookies or SSO credentials. |
| **Anti-bot aggregators** | Boards with Cloudflare Turnstile or PerimeterX | **Rate-limited** | Automated HTTP requests may trigger HTTP 403 blocks without proxy rotation. |

## Model context protocol (MCP) integration

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
| `export_report` | `json_source` *(optional)*, `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `formats` *(default `['pdf']`; supports `pdf`, `png`, `csv`, `json`)*, `candidate_name` *(default `'Job Seeker'`)*, `output_dir` *(optional)* | Regenerates a PDF, PNG, CSV, or JSON report from an existing sweep result without re-running discovery or scoring. |

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

Sweepy produces a card-style PDF report and can rasterize it to PNG. A real, single-page example (top 4 roles from the `paralegal_nyc` profile, live LinkedIn postings) commits for review:

- [Sample report (PDF)](docs/sample_report.pdf)
- [Sample report, page 1 (PNG)](docs/sample_report.png)

Regenerate both with `python scripts/make_sample.py`.

## Legal and responsible use

Sweepy uses `python-jobspy` to scrape public job boards including LinkedIn, Indeed, Glassdoor, and ZipRecruiter without API keys. It also fetches the public Greenhouse and Lever job-board APIs, the Ashby and Workable APIs, and Built In NYC pages directly. Scraping may violate the Terms of Service of some platforms. You are responsible for how you use this tool.

- This project targets **personal job searching**, not bulk data collection or redistribution.
- Respect rate limits and the target sites' policies. Don't hammer endpoints. Sweepy sends a polite User-Agent and a small inter-request delay (override with the `SWEEPY_SOURCE_DELAY` environment variable).
- Sweepy doesn't provide legal advice. Review the ToS of any platform you query before relying on it.

See [`python-jobspy`](https://github.com/Bunsly/JobSpy) for the upstream scraper and its own usage notes.

## Module reference
- `swee.py`: Primary orchestrator and `argparse` command-line entry point.
- `server.py`: Model Context Protocol (`stdio`) server exposing tools for large language model (LLM) automation.
- `engine/config.py`: Interactive command-line wizard and YAML parsing logic.
- `engine/discovery.py`: Scraper orchestration (jobspy + deterministic sources), ATS detection, and deduplication.
- `engine/sources/`: Deterministic Greenhouse, Ashby, Lever, Workable, and Built In NYC fetchers with seed lists in `data/sources/`.
- `engine/validator.py`: URL uptime checking and HTTP soft 404 detection.
- `engine/scorer.py`: Resume keyword extraction, percentage matching, and tagging.
- `engine/enrich.py`: Deterministic card enrichment—summaries, requirements, comp, resume-track routing, and match provenance.
- `engine/session.py`: Thread-safe card-record store backing the MCP hybrid stateful flow.
- `engine/report.py`: The default card-layout PDF renderer (faithful port of the reference layout).
- `engine/pdf_builder.py`: The legacy table-layout PDF renderer (`report.style: legacy`).
- `engine/exporter.py`: CSV and JSON export, plus PNG rasterization of report PDFs.

## License

Sweepy releases under the [MIT License](LICENSE).
