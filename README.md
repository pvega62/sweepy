# Sweepy

[![M8ven Score](https://m8ven.ai/badge/mcp/pvega62-sweepy-07ewva?v=a2ea0bac35a4ed6e7512771f55ab2271)](https://m8ven.ai/mcp/pvega62-sweepy-07ewva?s=readme)

Sweepy is a free tool that sweeps the internet for job postings and scores each one against your resume. It pulls openings from company career sites and job boards, then drops duplicates and expired listings. Every run leaves you one ranked report to work through. The setup wizard opens a main menu where you can run a sweep or create and reopen profiles. You can also toggle debug logging and tune the scoring weight, with aggregator management available from the same menu. Sweepy writes every file it needs.

## Features

- **Searches many places at once.** Collects postings from Greenhouse, Ashby, Lever, Workable, Built In New York City, LinkedIn, Indeed, Glassdoor, and ZipRecruiter. Each source works without an API key.
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

Running `sweepy` opens the wizard's tile-based launchpad. Use the arrow keys to move between **Launch Sweep**, **Build Profile**, **Load Profile**, **Tune Search**, and **Open Toolbox**, then press Enter. **Load Profile** lets you choose a saved profile to use for the next sweep. The toolbox contains profile editing, source management, debug logging, help, recent logs, document conversion, updates, and exit. **Build Profile** collects your name, target job titles, location, and resume path. The wizard saves the profile when you finish. Run `sweepy --setup --profile profiles/your_profile.yaml` to edit a profile directly.

To pull the latest code when a new version ships, run:

```bash
sweepy --update
```

Sweepy checks your Git remote, fast-forwards the checkout, and reinstalls `requirements.txt`. It refuses to touch a checkout with uncommitted changes. Prefer `sweepy --check-update` to see whether a new version exists without changing anything.

Then run your first sweep:

```bash
sweepy --run
```

`--run` sweeps with the last profile you saved. To name a different profile, use `sweepy --profile profiles/your_profile.yaml`.

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

Scraping runs through [`python-jobspy`](https://github.com/Bunsly/JobSpy). That project publishes its own usage notes.

## License

Sweepy releases under the [MIT License](LICENSE).
