# Career Sweep Engine

**Career Sweep Engine** is a free Python automation tool. It aggregates, de-duplicates, and scores job postings across multiple ATS platforms and job boards. It uses dynamic PDF resume parsing to score matches. Finally, it generates structured datasets and highly readable 4-card-per-page PDF reports.

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
git clone https://github.com/pvega62/career-sweep-engine.git
cd career-sweep-engine
pip install -r requirements.txt
```

Verify your installation:
```bash
python sweep.py --version
```

## Command-line usage

### 1. Interactive setup wizard
Use the built-in questionary command-line tool to generate a YAML configuration profile:
```bash
python sweep.py --setup
```

### 2. Execution pipeline
Run the engine by passing a configuration profile. The engine executes a 5-stage pipeline:
1. **Profile loading**: Parses YAML and validates constraints.
2. **Discovery**: Executes scrapers across configured ATS platforms and aggregates postings.
3. **Validation**: Prunes dead links and parses soft 404 redirects.
4. **Scoring**: Parses the provided resume PDF, calculates keyword overlap, and generates custom application playbooks.
5. **Generation**: Builds the date-stamped PDF, CSV, and JSON payloads.

```bash
python sweep.py --profile profiles/your_custom_profile.yaml
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

## Module reference
- `sweep.py`: Primary orchestrator and `argparse` command-line entry point.
- `engine/config.py`: Interactive command-line wizard and YAML parsing logic.
- `engine/discovery.py`: Scraper orchestration, ATS detection, custom platform matching, and DataFrame de-duplication.
- `engine/validator.py`: URL uptime checking and HTTP soft 404 detection.
- `engine/scorer.py`: Resume keyword extraction, percentage matching, and tagging.
- `engine/pdf_builder.py`: PDF generation with customized `reportlab` layouts.
- `engine/exporter.py`: DataFrame restructuring and CSV or JSON exporting.
