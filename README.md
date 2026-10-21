# Sweepy

[![M8ven Score](https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271)](https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme)

Sweepy is a free tool that searches job boards and scores each posting against your resume. It collects openings from company career sites and job boards, checks for duplicate listings across boards, removes expired listings, and creates a ranked report. You can disable duplicate checking for a single sweep without changing your profile. The setup wizard opens a launchpad for searches, profile setup, search tuning, and Sweepy's Toolbox tasks such as engine and aggregator management.

See [CHANGELOG.md](CHANGELOG.md) for the current version and release history.

## Features

- **Searches many places at once.** Collects postings from Greenhouse, Ashby, Lever, Workable, Built In New York City, LinkedIn, Indeed, Glassdoor, and ZipRecruiter. Each source works without an API key.
- **Runs every engine in parallel.** Enabled engines start together. A sweep then takes about as long as the slowest engine rather than the sum of them.
- **Keeps going when a board fails.** Each engine gets a timeout and a circuit breaker. One failing endpoint can't stall the run or repeat the same request five times.
- **Adds more engines on demand.** Install HireHunt, openroles, jobdrop, or Apify from the wizard without leaving the terminal.
- **Scores every posting against your resume.** Reads the text of your PDF or Word resume and measures how much of it matches the posting.
- **Filters out expired links.** Checks each URL and removes the postings that no longer exist.
- **Checks for duplicate postings across boards.** Matches normalized job title, company, and location, even when boards use different URLs. Pass `--no-dedupe` to keep every board's listing for one run.
- **Skips postings you already saw.** A daily sweep reports new roles instead of yesterday's list. Reported postings stay hidden for a four-day window, and `--include-seen` brings them back for one run.
- **Routes you to the right resume.** Sends each job to the resume track you wrote for that role, then labels the card with a color badge.
- **Builds a report you can use.** Produces a card-per-page PDF with clickable links, plus CSV and JSON files for your own tracking.
- **Turns the CSV into an application tracker.** The CSV ends with `date_applied`, `status`, `interview_stage`, `offer_amount`, `offer_date`, `follow_up_date`, `contact`, and `notes`. Fill them in through Excel, Google Sheets, or Notion. Sweepy copies your entries into later sweeps of the same profile. The PDF gives you one ranked reading list with apply links on each card. The spreadsheet keeps roles past the PDF card limit and records what you did about each one. Turn the columns off with `export.tracking: false`.

## Quick start

You need **Python 3.10 or newer**. On Python 3.13, some packages build from source, so you may need the Microsoft C++ Build Tools first. See [Installation](https://pvega62.github.io/software/docs/sweepy/installation).

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` installs every core dependency and registers the `sweepy` command in your Python Scripts folder. Reopen your terminal once so that folder lands on PATH. Run `sweepy` to start the wizard, or add a command option such as `sweepy --run`. You can also run the script directly with `python swee.py`.

That one command gives you the two built-in engines. The wizard offers the four optional engines when you need them, and you never run a separate requirements file.

To pull every compatible engine up front instead, add one flag to the same command:

```bash
pip install -e ".[all-engines]"
```

That adds HireHunt, openroles, and Apify in one resolution. `jobdrop` stays out because its metadata cannot resolve next to JobSpy. Install it with `sweepy --install-engines jobdrop --allow-engine-conflicts` when you want its 33 boards. The [Job engines](#job-engines) section covers both paths.

Running `sweepy` opens the wizard's tile-based launchpad. Use the arrow keys to move between **Launch Sweep**, **Build Profile**, **Load Profile**, **Sweep Settings**, **Sweepy's Toolbox**, and **Exit Sweepy**, then press Enter. Each tile's subtitle states the action in a few plain words, such as **Run your job search now**, **Open a search you saved**, or **Ranking, cards, tracking**. **Load Profile** lets you choose a saved profile to use for the next sweep. The toolbox contains profile editing, engine management, debug logging, help, recent logs, document conversion, and updates. **Build Profile** collects your name, target job titles, location, and resume path. The wizard saves the profile when you finish. Run `sweepy --setup --profile profiles/your_profile.yaml` to edit a profile directly.

Submenus open with **← Back**, which returns to the menu that opened them. Esc does the same. At a question, Esc reopens the previous answer. Inside a submenu, Esc steps up one level. At the launchpad, Esc exits. Ctrl+C quits from anywhere.

To pull the latest code when a new version ships, run:

```bash
sweepy --update
```

Sweepy checks your Git remote, fast-forwards the checkout, and reinstalls `requirements.txt` along with any optional engines you already installed. It refuses to touch a checkout with uncommitted changes. Prefer `sweepy --check-update` to see whether a new version exists without changing anything.

Then run your first sweep:

```bash
sweepy --run
```

`--run` sweeps with the last profile you saved. To name a different profile, use `sweepy --profile profiles/your_profile.yaml`.

Disable duplicate checking for one run without editing or saving a profile setting:

```bash
sweepy --run --no-dedupe
sweepy --profile profiles/your_profile.yaml --no-dedupe
```

By default, Sweepy keeps one posting when different boards list the same normalized title, company, and location. The MCP `run_sweep` tool accepts `deduplicate=false` for the same per-run override.

Sweepy also hides postings from earlier sweeps. Review them again or start over:

```bash
sweepy --run --include-seen      # report earlier postings too
sweepy --run --reset-history     # forget them, then sweep
sweepy --reset-history           # forget the last profile's history and exit
```

Build or update a profile without prompts when you script Sweepy:

```bash
sweepy --setup --non-interactive \
  --name "Alex Rivera" \
  --titles "Technical Writer,UX Writer" \
  --location "New York, NY" \
  --resume C:/resumes/alex.pdf \
  --sources jobspy,openroles \
  --openroles-companies figma,stripe,notion \
  --timeout 120 --no-cache
```

Every enabled engine validates before the file is written, so a missing required field fails fast with the reason. In the interactive wizard, leave OpenRoles company slugs blank to skip that engine; OpenRoles only searches named company boards. Non-interactive profiles that enable OpenRoles still need `--openroles-companies`. Non-interactive flags cover `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, `--no-cache`, `--history-days`, `--no-history`, and `--job-tracking` / `--no-job-tracking`.

Fill in a profile file when you prefer an editor to prompts and tool calls:

```bash
cp profiles/template_custom.yaml profiles/my_search.yaml
# replace the four REQUIRED values, then run the copy
sweepy --profile profiles/my_search.yaml
```

The template documents every setting with its default. Sweepy prints your name, titles, and location before discovery starts. A typo shows up on the first output line.

Convert a resume or notes file to PDF without opening the wizard:

```bash
sweepy --convert path/to/resume.docx
```

`--convert` accepts `.docx`, `.doc`, `.txt`, `.md`, and `.pdf` files. It writes the PDF beside the original file and prints the final path.

A sweep takes 30 to 90 seconds. Sweepy prints its progress as it works:

1. **Loads your profile.**
2. **Discovers openings** across the platforms you turned on.
3. **Validates links** and drops the expired ones.
4. **Scores each role** against your resume.
5. **Writes your report.**

## What you get

Every run writes date-stamped files to the `results/` folder, so nothing you already have gets overwritten.

- **A PDF report.** One card per role, sorted by match score, with pay, benefits, and a link to apply.
- **A CSV file.** Every card field plus a 1,000-character posting excerpt, plus eight job-tracking columns that Sweepy copies into later sweeps. Open it in Excel, Google Sheets, or Notion.
- **A JSON file.** The same data in a format other tools can read.

Open the [sample PDF](docs/sample_report.pdf), or view [page 1 as an image](docs/sample_report.png).

## Job engines

Sweepy includes two engines and can download four more. Every engine runs behind the same adapter, so profiles look the same no matter which one found the posting.

| Engine | Availability | What it scrapes | Proxies | User-Agent | Descriptions |
|---|---|---|---|---|---|
| `jobspy` | Built in | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | Yes | Yes | Toggle |
| `ats` | Built in | Greenhouse, Ashby, Lever, Workable, Built In NYC | No | No | Always |
| `hirehunt` | Download | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, and six FAANG boards | No | No | Always |
| `openroles` | Download | Greenhouse, Lever, Ashby, Workday boards you name | No | No | Always |
| `jobdrop` | Download | 33 boards including Google, Wellfound, Workday, iCIMS, Dice, USAJobs | Yes | Yes | Toggle |
| `apify` | Download | Managed actors, LinkedIn by default | Handled by actor | Handled by actor | Actor-dependent |

`jobdrop` reports a metadata conflict with JobSpy: it pins `curl-cffi<0.8`, while JobSpy requires `curl_cffi>=0.16.2`. The pin is stale. `jobdrop` runs fine on the newer library, which still ships every impersonation profile it uses (`safari17_2_ios`, `chrome120`, `chrome124`).

A plain `pip install` of both still fails, so `--install-engines all` leaves `jobdrop` out. Add `--allow-engine-conflicts` to install it the supported way. Sweepy installs `jobdrop` with `--no-deps`, then resolves its other requirements, so `curl_cffi` stays at JobSpy's version and both engines run.

```bash
sweepy --install-engines all
sweepy --install-engines openroles,apify
sweepy --install-engines jobdrop --allow-engine-conflicts
```

`pip check` still reports `jobdrop`'s stale upper bound after that install. The warning describes the metadata, not the running code.

Or open the wizard and choose **Sweepy's Toolbox** then **Download job engines**. That screen lists each engine's boards and install state. It asks before it runs `pip`. Pick a missing engine while building a profile and the wizard offers the same download. Sweepy never runs an install without your confirmation.

### Disk footprint

Measured on Windows with Python 3.13:

| Install | Packages on disk | Notes |
|---|---|---|
| Core (`requirements.txt`) | 290 MB | 53 packages, including pandas, pymupdf, and the MCP SDK |
| `hirehunt` | +12 MB | Adds rich and markdown-it-py |
| `openroles` | +0.3 MB | Python standard library only |
| `apify-client` | +17 MB | Adds impit, pydantic extras, and dnspython |
| `jobdrop` | +406 MB | Led by scipy (134 MB), playwright (113 MB), tls-client (93 MB), and selenium (34 MB) |

A full install of the compatible engines takes about **320 MB**. Forcing `jobdrop` in as well brings the package total to about **715 MB**, before it downloads a browser.

Browser binaries live outside the Python environment and arrive on first use:

- Playwright's Chromium build is about **710 MB** (Chromium plus its headless shell).
- A full Playwright set, including Firefox and WebKit, runs about **1.2 GB**.
- Camoufox, which `jobdrop` uses for its stealth path, downloads a patched Firefox on first launch.

Sweepy runs every built-in engine without a browser. The core install needs none of that space.

List engines and their install state at any time:

```bash
sweepy --list-engines
```

`openroles` reads boards you name, so it requires company slugs. `apify` reads an `APIFY_TOKEN` environment variable and bills against your Apify account.

Installing an engine does not switch it on. Add it to a profile in one of three ways:

1. **Wizard.** Run `sweepy`, choose **Sweepy's Toolbox**, then **Manage job engines**, then **Choose engines and settings**. Installed engines show an `[installed]` tag. Tick one and the wizard prompts for its settings.
2. **Profile edit.** Load the profile, then pick **Manage job engines** from the review screen.
3. **Command line.** Name the engine in `--sources` and supply its settings:

```bash
sweepy --setup --non-interactive --profile profiles/your_profile.yaml \
  --sources jobspy,ats,jobdrop --jobdrop-sites linkedin,indeed,wellfound
```

Each route validates the engine's settings before it writes the file. A missing value, such as `openroles` company slugs, fails with the reason instead of saving a broken profile.

### Choosing boards

The profile wizard's platform step lists every board Sweepy can search, grouped under the engine that reads it. All 63 boards appear in one place instead of only the built-in five.

| Group | Boards | Tag |
|---|---|---|
| `jobspy` (8) | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, Bayt, Naukri, BDJobs | `built in` |
| `ats` (5) | Greenhouse, Ashby, Lever, Workable, Built In NYC | `built in` |
| `hirehunt` (12) | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, Google Careers, Amazon, Meta, Apple, Netflix, Microsoft | `needs download` until installed |
| `openroles` (4) | Greenhouse, Lever, Ashby, Workday | `needs download`, and needs company slugs |
| `jobdrop` (33) | Google, Wellfound, Workday, iCIMS, Dice, USAJobs, Handshake, and more | `needs download`, and conflicts with JobSpy |
| `apify` (1) | LinkedIn through an Apify actor | `needs download`, and needs an `APIFY_TOKEN` |

Each row shows its engine and install state, such as `Indeed  [jobspy · built in]` or `Wellfound  [jobdrop · needs download]`. You see the tag before you commit to the choice. Tick a board from an engine with no local install and the wizard prints the command that installs it. An installed engine shows `installed` instead. Reopening a saved profile shows its current boards already ticked, and Sweepy keeps a board from an uninstalled engine in the profile: the sweep skips that engine with a warning until the install finishes.

### Engine settings

```yaml
sources:
  enabled: [jobspy, ats, openroles]
  openroles:
    ats: [greenhouse, lever, ashby, workday]
    companies: [figma, stripe, notion]
  jobdrop:
    sites: [linkedin, indeed, google, glassdoor]
    headless: true
    fetch_descriptions: true
    proxies: ["user:pass@host:port"]
cache:
  enabled: true
  ttl_seconds: 3600
history:
  enabled: true
  retention_days: 4
  match: url+role
  path: null
orchestrator:
  timeout_per_source_seconds: 180
  circuit_breaker:
    failure_threshold: 5
    cooldown_seconds: 30
```

Older profiles keep working. The board booleans under `sources.jobspy` still turn individual JobSpy boards on and off. Any profile without a `sources.enabled` list defaults to JobSpy plus the built-in ATS readers.

- **Descriptions stay on by default.** Scoring matches posting text against your resume. Turn `fetch_descriptions` off only if you accept weaker matches for a faster sweep.
- **Proxies stay opt-in per engine.** The wizard reads them from a file or accepts one inline, hides the password while you type, and never prints the contents. `hirehunt` lacks a proxy hook, so Sweepy logs a warning when a profile configures one.
- **The cache starts on.** A repeated query with the same engines and settings returns the previous results for an hour. Clear it with `cache.enabled: false`, or shorten `ttl_seconds`.
- **Timeouts stop at the boundary.** Python can't kill a thread that already blocks inside a library call. Sweepy stops waiting and moves on, and each library applies its own HTTP timeouts underneath.
- **The circuit breaker skips a sick engine.** After five consecutive failures, Sweepy stops calling that engine for 30 seconds and reports it in `skipped_sources`.

### Previously reported postings

Sweepy records every posting it reports and skips the same posting on the next sweep. The record lives in `~/.sweepy/history.db`, scoped per profile. Set `SWEEPY_HISTORY_PATH` to store it elsewhere. The wizard's **Sweep Settings** screen exposes the on/off switch and the retention window.

```yaml
history:
  enabled: true
  retention_days: 4   # 0 reports every posting on every run
  match: url+role     # url (strict) or url+role (default)
  path: null          # null uses ~/.sweepy/history.db
```

- **Retention is a re-report cadence.** A posting stays hidden until `retention_days` pass, then it can appear again. A continuously live listing returns at most every four days.
- **Matching is forgiving by default.** Sweepy compares canonical URLs, with tracking parameters and fragments removed, and falls back to normalized title, company, and location so a repost on another board counts as the same role. Set `match: url` to require a canonical URL match.
- **Only live postings count.** A posting enters history after its URL passes validation, so dead links never become invisible.
- **MCP callers get the same default.** `run_sweep` reports `previously_seen_count` and `new_count`; pass `include_seen=true` to review earlier postings, and call `clear_history` to forget them. `create_profile` accepts `history_config`.

### Adding another engine

1. Create `engine/adapters/<name>_adapter.py` and subclass `ScraperAdapter`.
2. Set `name`, the three `supports_*` flags, `default_concurrency`, and `library`.
3. Write `preflight()` to check config and `scrape()` to return a DataFrame.
4. Register it in `engine/adapters/__init__.py`.
5. Describe it in `engine/engines.py` so the wizard can show and install it.
6. Add a config block to `engine/sweep_config.py` and a prompt to `_ENGINE_PROMPTS`.
7. Add the package to `requirements-engines.txt` and the pyproject extras.
8. Test the adapter on its own, then enable it alone during a sweep.

The orchestrator handles the rest. It dispatches by name and enforces the timeout. Any frame that comes back gets normalized.

## Agent judgment (default in MCP)

Sweepy scores postings by shared vocabulary, which keeps a sweep free, offline, and repeatable. That score measures wording, not fit, so the MCP server treats an agent assessment as the expected path.

`run_sweep` does not call a model. It returns `assessment_mode: "agent"`, `assessment_required: true`, and `assessed_count: 0`. The workflow continues with `get_jobs`, an independent assessment of each role against the résumé, `submit_judgments`, and `render_report`. Pass every judgment in one `judgments` list to keep a 24-role assessment to a single call. Assessed cards show `NN% MATCH`; unassessed cards keep `NN% KEYWORD OVERLAP`.

`render_report` takes a `playbook` argument for the closing strategy box. Write plain prose: Sweepy escapes ampersands and angle brackets, turns newlines into line breaks, and renders `**bold**`. The text saves with the session, so a later render keeps it instead of reverting to the generated playbook. A new sweep clears it.

In `agent` mode, `render_report` refuses to build a mixed report. It returns an error listing the unassessed job ids so the assistant knows what to judge. Profiles that want keyword-only reports set `report.assessment: "keyword"`, which is the CLI's behavior. Set `SWEEPY_REQUIRE_JUDGMENTS=1` when the gate must apply to every profile and to `export_report` as well.

A live sweep scrapes boards for minutes, so the MCP server runs it in the background. `run_sweep` waits at most 45 seconds and then returns `sweep_status: "running"` with a `job_id`. Poll `get_sweep_status` until it reports `completed`; the sweep keeps running if the client disconnects. Set `SWEEPY_MCP_WAIT_SECONDS` to lower the wait for hosts with tighter tool timeouts.

MCP-created profiles use built-in engines and installed optional engines that pass
their default configuration checks. Provide `sources_config` to choose engines
explicitly. OpenRoles needs company slugs, and Apify requires explicit opt-in because
it may incur charges.

The assistant can verify results and fill coverage gaps with its search tools. It should
inspect skipped sources, check postings against employer career pages, and add verified
omissions to the report. It must label inaccessible listings as unverified and disclose
when it cannot confirm complete coverage.

Read [MCP integration](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration) for the setup steps.

Every MCP tool declares read-only, destructive, idempotent, and open-world hints so compatible hosts can identify its behavior before invocation.

## Before you upload your resume

Your layout decides how much text Sweepy can read. A two-column design, a table, or a scanned page scrambles what the engine sees and lowers your scores. One clean column of real text extracts best, and applicant tracking systems read it the same way.

Read [Resume formatting tips](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips) before your first sweep.

## Documentation

### Getting started

- [Introduction](https://pvega62.github.io/software/docs/sweepy/intro)
- [Installation](https://pvega62.github.io/software/docs/sweepy/installation)
- [Configuration](https://pvega62.github.io/software/docs/sweepy/configuration)
- [Running your first sweep](https://pvega62.github.io/software/docs/sweepy/first-sweep)
- [Understanding your results](https://pvega62.github.io/software/docs/sweepy/understanding-results)

### Resumes and match scores

- [Resume formatting tips](https://pvega62.github.io/software/docs/sweepy/guides/resume-tips)
- [Scoring and limits](https://pvega62.github.io/software/docs/sweepy/guides/scoring-and-limits)

### Command and configuration reference

- [Commands and flags](https://pvega62.github.io/software/docs/sweepy/reference/cli-reference)
- [Configuration reference](https://pvega62.github.io/software/docs/sweepy/reference/configuration-reference)
- [Job sources and platforms](https://pvega62.github.io/software/docs/sweepy/reference/sources-and-platforms)
- [MCP integration](https://pvega62.github.io/software/docs/sweepy/reference/mcp-integration)
- [MCP tool reference](https://pvega62.github.io/software/docs/sweepy/reference/mcp-tool-reference)
- [Developer reference](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## Legal and responsible use

Sweepy scrapes public job boards and job-board APIs. Scraping may violate the terms of service of some platforms, so review those terms before you rely on the tool.

- Use it for **personal job searching**, not bulk collection or redistribution.
- Respect rate limits. Sweepy sends a polite User-Agent and a short delay between requests. Raise the delay with the `SWEEPY_SOURCE_DELAY` environment variable.
- Sweepy doesn't offer legal advice.

Scraping runs through [`python-jobspy`](https://github.com/Bunsly/JobSpy) and, when you install them, [`hirehunt`](https://pypi.org/project/hirehunt/), [`openroles`](https://pypi.org/project/openroles/), [`jobdrop`](https://pypi.org/project/jobdrop/), and [Apify](https://apify.com/). Each project publishes its own usage notes. Google Jobs, LinkedIn, Indeed, and Glassdoor scraping may violate those platforms' terms of service. Apify moves the request to a managed service; it does not change the legal risk.

## License

Sweepy releases under the [MIT License](LICENSE).
