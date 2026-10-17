---
name: sweepy
description: Use /sweepy to find jobs through Sweepy's MCP, assess roles against the user's resume with LLM judgments, review matches, and export reports.
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

## Start a new LLM-assisted search

1. Call `create_profile` with the candidate's name, target job titles, location, and
   resume PDF path. Optional fields (remote/hybrid preference, minimum salary,
   must-have skills) use sensible defaults when omitted.
2. Call `run_sweep` with the saved profile path. This discovers and validates postings,
   then generates deterministic keyword-overlap scores. It does not perform LLM
   assessment by itself; tell the user that these initial scores are preliminary.

## Assess and report matches

- By default, do not stop at keyword scores and do not wait for the user to request the
  LLM boost. Call `get_jobs` to inspect the available details for relevant roles.
- Compare each assessable role with the candidate's resume and stated preferences. Submit
  an independent `match_pct` and evidence-grounded card fields through `submit_judgments`.
  Never copy the deterministic overlap score into `match_pct` or invent unsupported job
  requirements. If evidence is insufficient, disclose the limitation and retain the
  `KEYWORD OVERLAP` label for that role.
- Call `render_report` after submitting judgments so the PDF reflects assessed matches.
- Call `get_results` for initial sweep metadata, but treat scores labeled `KEYWORD OVERLAP`
  as unassessed. Present `NN% MATCH` only for cards with submitted LLM judgments.

Use a keyword-only scrape and report only when the user explicitly requests deterministic
keyword results or available job evidence cannot support responsible LLM assessment.

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
python swee.py --convert notes.md      # convert any supported document to PDF
```

## Notes

- `run_sweep` produces deterministic `NN% KEYWORD OVERLAP` scores; it does not invoke an
  LLM automatically. The default MCP-assisted workflow is
  `run_sweep → get_jobs → assess roles → submit_judgments → render_report`.
- `submit_judgments` upgrades a card to `NN% MATCH` only when the assistant supplies an
  independent, evidence-based assessment.
