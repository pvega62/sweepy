# Career Sweep Engine

**Career Sweep Engine** is a customizable, zero-API-cost Python tool designed to automate job board sweeping, parsing, and scoring across multiple platforms (LinkedIn, Indeed, Glassdoor, ZipRecruiter).

## Features
- **Multi-Platform Scraping**: Built on the open-source `jobspy` library to search across major job boards without API keys.
- **Configurable Profiles**: Define reusable YAML profiles to search for entirely different careers (e.g., Paralegal, Front End Developer, UX Writer) seamlessly.
- **Automated Validations**: Uses `requests` to verify if job links are still active (including platform-specific dead pages like Ashby's soft 404s).
- **Match Scoring**: Extracts text from your PDF resume via `PyMuPDF` and assigns a match percentage based on your defined "must-have" skills.
- **Visual Reporting**: Generates a clean, readable 4-card-per-page PDF using `reportlab`. Cards are color-coded (Amber for jobs requiring extended responses, Slate for quick applies).
- **Export Ready**: Save results as PDF, CSV, and JSON for further tracking in Notion, Excel, or Google Sheets.

## Installation

Ensure you have Python 3.10+ installed. 

> **Note for Python 3.13 Users:** Since Python 3.13 is very new, some packages like `pymupdf` do not yet have pre-compiled binaries. You must install the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) ("Desktop development with C++" workload) to allow pip to compile them from source.

```bash
git clone <your-repo-url>
cd career-sweep-engine
pip install -r requirements.txt
```

## Quick Start

The easiest way to get started is by running the interactive setup wizard:

```bash
python sweep.py --setup
```

The wizard will ask you questions about your target role, location, skills, and export preferences. It generates a custom profile in the `profiles/` directory.

To run a sweep using your new profile:

```bash
python sweep.py --profile profiles/<your_name>_profile.yaml
```

## Creating Custom Profiles

You can manually create or duplicate profiles in the `profiles/` folder to quickly switch between different job searches. See `profiles/paralegal_nyc.yaml` or `profiles/frontend_developer.yaml` for examples.

### Example Profile

```yaml
name: "Alex"
search:
  titles:
    - "Paralegal"
    - "Legal Assistant"
  location: "New York, NY"
  remote_only: false
  min_salary: 60000
resume:
  path: "C:/path/to/alex_paralegal_resume.pdf"
  must_have_skills:
    - "Contract Review"
    - "Legal Research"
    - "Westlaw"
    - "LexisNexis"
    - "Drafting"
  keywords_weight: 1.5
export:
  format: "pdf,csv"
  output_dir: "results"
```

## Architecture & Code

- `sweep.py`: Main CLI entry point.
- `engine/config.py`: Interactive CLI wizard (`questionary`) and YAML configuration loading.
- `engine/discovery.py`: Scraper orchestration using `jobspy`.
- `engine/validator.py`: URL liveness checking and soft-404 detection.
- `engine/scorer.py`: Resume extraction (`fitz`) and match-percentage calculation.
- `engine/pdf_builder.py`: Report generation using `reportlab`.
- `engine/exporter.py`: CSV/JSON dumping using `pandas`.
