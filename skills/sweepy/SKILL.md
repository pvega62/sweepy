---
name: sweepy
description: Run the Sweepy job search engine from this CLI. Use /sweepy to create a search profile, scrape and score jobs, review matches, and export CSV/PDF reports through Sweepy's MCP server.
---

# Sweepy

Sweepy aggregates, de-duplicates, and scores job postings across ATS boards and job
boards. This skill drives Sweepy through its MCP server (`server.py`) so the tools are
available directly in this conversation.

## When to use

Use `/sweepy` when the user wants to search for jobs, run a sweep, review matches, or
export a CSV/PDF report.

## Setup (once)

Register Sweepy's MCP server in the CLI's MCP configuration:

```json
{
  "mcpServers": {
    "sweepy": {
      "command": "python",
      "args": ["/path/to/sweepy/server.py"]
    }
  }
}
```

Replace `/path/to/sweepy` with the absolute path to the repository. Restart the CLI
after editing the configuration.

## Start a new scrape

1. Call `create_profile` with the candidate's name, target job titles, location, and
   resume PDF path. Optional fields (remote/hybrid preference, minimum salary,
   must-have skills) use sensible defaults when omitted.
2. Call `run_sweep` with the saved profile path. This discovers, validates, scores,
   and renders the report in one pass and returns the top roles and report paths.

## View the results of a scrape

- Call `get_results` to retrieve the top matches with scores, companies, locations,
  and playbook recommendations without re-running discovery.
- Call `get_jobs` to inspect the full deterministic card set in the current session
  before supplying any LLM judgment.

## Export results to a CSV file

Call `export_report` with `formats=["csv"]` (optionally add `"pdf"`, `"json"`, or
`"png"`). Pass `json_source` to target a specific sweep result, or `profile_stem` to
pick the latest result for a profile. Use `output_dir` to control where the files land.

## CLI fallback

When MCP tools are unavailable, run the CLI from the repository root:

```bash
python swee.py --setup                 # interactive profile wizard
python swee.py --profile profiles/your_profile.yaml
python swee.py --docx resume.docx      # convert a DOCX resume to PDF
```

## Notes

- Sweepy works with or without an LLM. Without an LLM it produces deterministic
  `NN% KEYWORD OVERLAP` scores; `submit_judgments` upgrades a card to an
  LLM-supplied `NN% MATCH`.
- The hybrid flow is `run_sweep → get_jobs → submit_judgments → render_report`.
