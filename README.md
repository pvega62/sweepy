# Sweepy

[![M8ven Score](https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271)](https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme)

Sweepy is a free tool that sweeps the internet for job postings and scores each one against your resume. It pulls openings from company career sites and job boards, then drops duplicates and expired listings. Every run leaves you one ranked report to work through. The setup wizard opens a main menu where you can run a sweep or create and reopen profiles. You can also toggle debug logging and tune the scoring weight, with aggregator management available from the same menu. Sweepy writes every file it needs.

## Features

- **Searches many places at once.** Collects postings from Greenhouse, Ashby, Lever, Workable, Built In New York City, LinkedIn, Indeed, Glassdoor, and ZipRecruiter. Each source works without an API key.
- **Runs every engine in parallel.** Enabled engines start together. A sweep then takes about as long as the slowest engine rather than the sum of them.
- **Keeps going when a board fails.** Each engine gets a timeout and a circuit breaker. One failing endpoint can't stall the run or repeat the same request five times.
- **Adds more engines on demand.** Install HireHunt, openroles, jobdrop, or Apify from the wizard without leaving the terminal.
- **Scores every posting against your resume.** Reads the text of your PDF or Word resume and measures how much of it matches the posting.
- **Filters out expired links.** Checks each URL and removes the postings that no longer exist.
- **Routes you to the right resume.** Sends each job to the resume track you wrote for that role, then labels the card with a color badge.
- **Builds a report you can use.** Produces a card-per-page PDF with clickable links, plus CSV and JSON files for your own tracking.

## Quick start

You need **Python 3.10 or newer**. On Python 3.13, some packages build from source, so you may need the Microsoft C++ Build Tools first. See [Installation](https://pvega62.github.io/software/docs/sweepy/installation).

```bash
git clone https://github.com/pvega62/sweepy.git
cd sweepy
pip install -e .
sweepy
```

`pip install -e .` installs every dependency and registers the `sweepy` command in your Python Scripts folder. Reopen your terminal once so that folder lands on PATH. Run `sweepy` to start the wizard, or add a command option such as `sweepy --run`. You can also run the script directly with `python swee.py`.

Running `sweepy` opens the wizard's tile-based launchpad. Use the arrow keys to move between **Launch Sweep**, **Build Profile**, **Load Profile**, **Tune Search**, **Open Toolbox**, and **Exit Sweepy**, then press Enter. **Load Profile** lets you choose a saved profile to use for the next sweep. The toolbox contains profile editing, engine management, debug logging, help, recent logs, document conversion, and updates. **Build Profile** collects your name, target job titles, location, and resume path. The wizard saves the profile when you finish. Run `sweepy --setup --profile profiles/your_profile.yaml` to edit a profile directly.

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

Every engine validates before the file is written, so a missing required field fails fast with the reason. Non-interactive flags cover `--sources`, `--jobspy-sites`, `--hirehunt-sources`, `--jobdrop-sites`, `--openroles-companies`, `--apify-actor`, `--timeout`, `--cache-ttl`, and `--no-cache`.

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
- **A CSV file.** Every field plus the full posting text. Open it in Excel, Google Sheets, or Notion.
- **A JSON file.** The same data in a format other tools can read.

Open the [sample PDF](docs/sample_report.pdf), or view [page 1 as an image](docs/sample_report.png).

## Job engines

Sweepy includes two engines and can download four more. Every engine runs behind the same adapter, so profiles look the same no matter which one found the posting.

| Engine | Availability | What it scrapes | Proxies | User-Agent | Descriptions |
|---|---|---|---|---|---|
| `jobspy` | Built in | LinkedIn, Indeed, Glassdoor, ZipRecruiter, Bayt, Naukri, BDJobs, HelloWork | Yes | Yes | Toggle |
| `ats` | Built in | Greenhouse, Ashby, Lever, Workable, Built In NYC | No | No | Always |
| `hirehunt` | Download | LinkedIn, Indeed, Naukri, Shine, Internshala, Unstop, and six FAANG boards | No | No | Always |
| `openroles` | Download | Greenhouse, Lever, Ashby, Workday boards you name | No | No | Always |
| `jobdrop` | Download | 33 boards including Google, Wellfound, Workday, iCIMS, Dice, USAJobs | Yes | Yes | Toggle |
| `apify` | Download | Managed actors, LinkedIn by default | Handled by actor | Handled by actor | Actor-dependent |

Install one engine, or every optional engine:

```bash
sweepy --install-engines all
sweepy --install-engines jobdrop,openroles
```

Or open the wizard and choose **Open Toolbox** then **Download job engines**. That screen lists each engine's boards and install state. It asks before it runs `pip`. Pick a missing engine while building a profile and the wizard offers the same download. Sweepy never runs an install without your confirmation.

`jobdrop` pulls browser automation for Playwright, Selenium, and Camoufox, so it needs the most disk space. Install the engine you need instead of `all` when bandwidth matters.

List engines and their install state at any time:

```bash
sweepy --list-engines
```

`openroles` reads boards you name, so it requires company slugs. `apify` reads an `APIFY_TOKEN` environment variable and bills against your Apify account.

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

## Add AI judgment (optional)

Sweepy scores postings by shared vocabulary, which keeps a sweep free, offline, and repeatable. Connect an AI assistant through the Model Context Protocol (MCP) when you want a second opinion on fit.

With a model connected, Sweepy relabels those cards `NN% MATCH` and lets the model write the summaries. Without one, you still get the full report.

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
- [Developer reference](https://pvega62.github.io/software/docs/sweepy/reference/developer-reference)

## Legal and responsible use

Sweepy scrapes public job boards and job-board APIs. Scraping may violate the terms of service of some platforms, so review those terms before you rely on the tool.

- Use it for **personal job searching**, not bulk collection or redistribution.
- Respect rate limits. Sweepy sends a polite User-Agent and a short delay between requests. Raise the delay with the `SWEEPY_SOURCE_DELAY` environment variable.
- Sweepy doesn't offer legal advice.

Scraping runs through [`python-jobspy`](https://github.com/Bunsly/JobSpy) and, when you install them, [`hirehunt`](https://pypi.org/project/hirehunt/), [`openroles`](https://pypi.org/project/openroles/), [`jobdrop`](https://pypi.org/project/jobdrop/), and [Apify](https://apify.com/). Each project publishes its own usage notes. Google Jobs, LinkedIn, Indeed, and Glassdoor scraping may violate those platforms' terms of service. Apify moves the request to a managed service; it does not change the legal risk.

## License

Sweepy releases under the [MIT License](LICENSE).
