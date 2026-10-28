---
name: sweepy
description: Use /sweepy to find jobs through Sweepy's MCP, ask for the user's portfolio and resume tracks, assess roles against them with LLM judgments, review matches, and export reports.
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

1. Ask the user for a portfolio before you build the profile. Accept an online URL, a
   local PDF, DOCX, Markdown, text, or HTML file, or none. Pass what they give you as
   `portfolios`, one entry per resume track when they target more than one role family,
   and pass `resume_tracks` when they keep a separate resume for each track. Sweepy lists
   each portfolio's pieces on the cards. For a saved profile, call `set_portfolio` instead.
2. Call `create_profile` with the candidate's name, target job titles, location, and
   resume PDF or DOCX path. Optional fields (remote/hybrid preference, minimum salary,
   must-have skills) use defaults when omitted. Without `sources_config`, the MCP
   enables built-in engines and installed optional engines that pass default
   configuration checks. Read and report `enabled_engines` and `engines_not_enabled`.
   OpenRoles only searches named company boards; the interactive wizard skips it when
   the user leaves company slugs blank. Apify may incur charges and requires explicit user
   opt-in. Do not ask the user to choose engines for every search or install packages
   automatically. Ask only when a requested engine needs configuration, paid-service
   consent, or a search constraint. Preserve any explicit `sources_config` unchanged.
   Set `cache_config.enabled` and `cache_config.ttl_seconds` to tune caching. Set
   `orchestrator_config.timeout_per_source_seconds` and its `circuit_breaker` fields
   to tune per-engine resilience. Set `history_config` (`enabled`, `retention_days`,
   `match`, `path`) to control how long reported postings stay hidden.
3. Call `run_sweep` with the saved profile path. This discovers and validates postings,
   then generates deterministic keyword-overlap scores. It does not perform LLM
   assessment by itself; tell the user that these initial scores are preliminary.
   Sweepy removes duplicate URLs and same-role postings across boards by default. Pass
   `deduplicate=false` to `run_sweep` to keep duplicates for one run without changing
   the saved profile.

   Sweepy also hides postings reported in earlier sweeps. The default retention window
   is four days. When the user asks for roles they saw before, pass `include_seen=true`
   or call `clear_history` to forget the profile's history. A sweep with no new postings
   reports `previously_seen_count` and a `message`; relay it as a normal result.
4. The pipeline scrapes live boards for minutes, so it runs in the background. When
   `run_sweep` returns `sweep_status: "running"`, call `get_sweep_status` with the
   returned `job_id` and repeat until it reports `completed`. Each call waits only its
   own `wait_seconds`, which keeps every request inside the client timeout. The sweep
   keeps running if the client disconnects.

## Compensate for scraper limits

- Treat Sweepy's results as a useful, non-exhaustive candidate set. Inspect
  `skipped_sources` from `run_sweep` and `engines_not_enabled` from `create_profile`.
  Report material failures; do not imply that every source returned results.
- Review jobs with `get_jobs`. Check each role against the user's preferences and
  resume, and submit corrected match assessments only when job details support them.
- If the host provides web or search tools, verify postings through employer career
  pages or their ATS and look for relevant roles Sweepy missed. Add only verified,
  non-duplicate roles with `import_jobs`, then include them in `render_report`.
- A 403, 429, timeout, or bot-protection response means the URL remains unverified;
  it does not show that a posting expired. Check an accessible employer source when
  possible. If you cannot confirm the status, label that uncertainty.
- Never fabricate listings or fill missing salary, requirements, or resume evidence
  with guesses. Without suitable search tools or accessible sources, explain that the
  result set may be incomplete. Do not repeat a sweep with unchanged inputs after a
  source error; retry only after a meaningful change or likely transient failure.

## Assess and report matches

- By default, do not stop at keyword scores and do not wait for the user to request the
  LLM boost. Call `get_jobs` to inspect the available details for relevant roles.
- Judge the resume document, not the profile. `get_jobs` returns `resume_documents` with
  the parsed text of every track. The profile's `must_have_skills` and `synonyms` only
  feed the deterministic keyword pass, so scoring from them measures the YAML instead of
  the candidate. Read the file the way a recruiter reads it: transferable skills, scope
  and seniority per bullet, domain, tools, and outcomes.
- Score the resume the way the posting's applicant tracking system parses it. A term the
  parser can read in a standard Experience or Skills section counts as evidence. The same
  term inside a table, header, footer, image, or two-column sidebar may never reach a
  person, so weigh it lower. Name the ATS family when the apply URL reveals it (Workday,
  Greenhouse, Lever, Ashby, iCIMS, Taleo, Workable, SmartRecruiters) and say in
  `concerns` what that parser would lose.
- Compare each assessable role with the candidate's resume and stated preferences. Submit
  an independent `match_pct` and evidence-grounded card fields through `submit_judgments`.
  Never copy the deterministic overlap score into `match_pct` or invent unsupported job
  requirements. If evidence is insufficient, disclose the limitation and retain the
  `KEYWORD OVERLAP` label for that role.
- State both sides of every assessment. `alignment` states the highlight: the strongest
  evidence that the candidate fits, plus the move that uses it. `concerns` states what
  works against the candidate: unmet requirements, seniority or tenure gaps, domain
  mismatches, on-site expectations, or pay below the floor. Cite the posting text, and
  write `None identified` only when the posting states no real obstacle. The card renders
  `concerns` as **Working Against You**. A one-sided pitch makes an incomplete
  assessment.
- Read `portfolio_pieces` on each card, pick the one to three pieces that fit the posting,
  and pass them to `submit_judgments` as `portfolio_highlight`. Leave it unset when the
  card has no portfolio. Tell the user which pieces you chose and why.
- Call `render_report` after submitting judgments so the PDF reflects assessed matches.
- Call `get_results` for initial sweep metadata, but treat scores labeled `KEYWORD OVERLAP`
  as unassessed. Present `NN% MATCH` only for cards with submitted LLM judgments.

Use a keyword-only scrape and report only when the user explicitly requests deterministic
keyword results or available job evidence cannot support responsible LLM assessment.

## Export results to a CSV file

Call `export_report` with `formats=["csv"]` (optionally add `"pdf"`, `"json"`, or
`"png"`). Pass `json_source` to target a specific sweep result, or `profile_stem` to
pick the latest result for a profile. Use `output_dir` to control where the files land.
A tracking-enabled profile adds `date_applied`, `status`, `interview_stage`,
`offer_amount`, `offer_date`, `follow_up_date`, `contact`, and `notes`. Sweepy copies
earlier entries into later exports. Pass `job_tracking` to override the profile setting.

## CLI fallback

When MCP tools are unavailable, run the CLI from the repository root:

```bash
python swee.py --setup                 # interactive profile wizard
python swee.py --profile profiles/your_profile.yaml
python swee.py --run --include-seen    # report postings from earlier sweeps too
python swee.py --run --reset-history   # forget earlier postings, then sweep
python swee.py --docx resume.docx      # convert a DOCX resume to PDF
python swee.py --convert notes.md      # convert any supported document to PDF
python swee.py --setup --non-interactive --profile profiles/your_profile.yaml \
  --portfolio https://example.com/work --portfolio "UX Writer=work/ux.pdf"
```

`--portfolio` takes a URL or a local PDF, DOCX, Markdown, text, or HTML file. Repeat it for
more sources, and prefix a value with a resume track name to attach it to that track.

## Notes

- `run_sweep` produces deterministic `NN% KEYWORD OVERLAP` scores; it does not invoke an
  LLM automatically. The default MCP-assisted workflow is
  `run_sweep → get_sweep_status → get_jobs → assess roles → submit_judgments → render_report`.
- `submit_judgments` upgrades a card to `NN% MATCH` only when the assistant supplies an
  independent, evidence-based assessment.
- Every card reports the portfolio for its resume track in `portfolio_url` and
  `portfolio_pieces`. `portfolio_highlight` holds the pieces the assistant chose to send.
- Sweeps skip postings reported in an earlier run for the same profile. The default
  retention window is four days; `include_seen=true` or `clear_history` overrides it.
