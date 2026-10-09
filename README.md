# Sweepy

**Sweepy** is a free Python automation tool. It aggregates, de-duplicates, and scores job postings across multiple ATS platforms and job boards. It uses dynamic PDF resume parsing to score matches. Finally, it generates structured datasets and highly readable 4-card-per-page PDF reports.

TL;DR: It **sweeps** the internet for job postings and scores them against your resume.

## Features and architecture
- **Multi-platform scraping**: Uses `python-jobspy` to extract postings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter without API keys.
- **ATS discovery and classification**: Inspects URLs to classify direct ATS endpoints, such as Greenhouse, Ashby, Lever, or Workable, versus aggregator feeds.
- **Dynamic scoring**: Dynamically extracts text from your PDF resume, computes a weighted overlap against the job description using `must_have_skills`, and identifies `missing_skills`.
- **Heuristic tagging**: Uses regex pattern matching to flag postings requiring extended written responses, such as "cover letter" or "assessment," versus standard quick applies.
- **Link validation**: Executes live HTTP `GET` requests to prune expired links and detect platform-specific soft 404 redirects, for example, Ashby returning a blank state.
- **Reporting**: Generates an atomic, styled PDF directory with clickable links and playbooks, alongside prioritized `.csv` and `.json` data dumps.

## Prerequisites
- **Python 3.10+**
- **Note for Python 3.13 users:** The `pymupdf` package may require source compilation if pre-built wheels are not available yet. Ensure you have the Microsoft C++ Build Tools installed and select the "Desktop development with C++." workload before you install dependencies.

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
4. **Scoring**: Parses the provided resume PDF, calculates keyword overlap, and generates custom application playbooks.
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

export:
  format: "pdf,csv,json"
  output_dir: "results"
```

## Custom platforms and caveats

You can register custom ATS domains under `platforms.custom` to classify postings directly into your report directory.

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
| `run_sweep` | `profile_path` *(optional)* | Runs the 5-stage sweep pipeline, parses results, and outputs a structured summary. |
| `get_results` | `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `limit` *(default `10`)* | Retrieves the top matching roles, playbook recommendations, and artifact paths from the most recent run. |
| `export_report` | `json_source` *(optional)*, `profile_stem` *(optional)*, `results_dir` *(default `'results'`)*, `formats` *(default `['pdf']`)*, `candidate_name` *(default `'Job Seeker'`)*, `output_dir` *(optional)* | Regenerates a PDF, CSV, or JSON report from an existing sweep result without re-running discovery or scoring. |

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

## Module reference
- `swee.py`: Primary orchestrator and `argparse` command-line entry point.
- `server.py`: Model Context Protocol (`stdio`) server exposing tools for large language model (LLM) automation.
- `engine/config.py`: Interactive command-line wizard and YAML parsing logic.
- `engine/discovery.py`: Scraper orchestration, ATS detection, custom platform matching, and DataFrame de-duplication.
- `engine/validator.py`: URL uptime checking and HTTP soft 404 detection.
- `engine/scorer.py`: Resume keyword extraction, percentage matching, and tagging.
- `engine/pdf_builder.py`: PDF generation with customized `reportlab` layouts.
