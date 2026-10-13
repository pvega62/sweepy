# Optimization Report

## Summary

Applied the full `CODE_CHANGES.md` brief (Tiers P0–P2) to Sweepy: corrected the correctness/safety defects (duplicate `main`, inverted `remote_only`, invalid `jobspy` kwarg, score floor, silent report overwrites, `--version` crash), replaced `print()`/`redirect_stdout` with disciplined `logging`, sandboxed MCP writes, parallelized validation, added progress reporting wired through to MCP clients, and added tests, CI, pinned deps, a changelog, and demo artifacts. Changes are left uncommitted in the working tree with suggested per-task commit messages below (per your instruction: no commits).

## Tasks completed

**P0-1** Removed the duplicate `main()`; kept the one with error handling.
**P0-2** Added `_WORKSPACE` sandbox (`SWEEPY_WORKSPACE`, `SWEEPY_ALLOW_EXTERNAL_WRITES`) + `_safe_output_path`/`_resolve_read_path`; routed all four tools' reads/writes through them.
**P0-3** Converted engine `print()` to module loggers (`sweepy.engine.*`).
**P0-4** Rewrote the wizard to ask "remote-only" and write `remote_only` directly (fixes inversion).
**P0-5** Replaced invalid `country_alice="usa"` with `country_indeed="usa"` (verified against installed `jobspy` 1.2.0 signature).
**P0-6** Parallelized `validator.py` (ThreadPoolExecutor, `_MAX_WORKERS=10`, HEAD-first with GET fallback, order-preserving).
**P0-7** Removed the `[50, 98]` clamp; zero-match jobs now score 0; added "Low match" PDF label for `<30`.
**P0-8** Report filenames now `{stem}_{YYYY-MM-DD}-{HHMMSS}.{ext}` (UTC time component).
**P0-9** `get_dependency_versions()` uses `importlib.metadata.version` with `PackageNotFoundError` → `MISSING`.
**P0-10** Replaced pipeline `print()` with `log_fn` (`verbose` flag); added `_quiet_stdout()` guards and documented stream discipline; removed the whole-pipeline `redirect_stdout`.
**P0-11** Logged per-title discovery failures (already wrapped; converted `print` → `log.warning`).

**P1-1** Added `progress(current, total, label)` to `run_sweep_pipeline` (5 stages) and to `discover_jobs`/`filter_valid_jobs`/`score_jobs`.
**P1-2** Made `run_sweep` async; runs the pipeline via `anyio.to_thread.run_sync` and forwards progress with `anyio.from_thread.run(ctx.report_progress, ...)`.
**P1-3** Added `include_roles` flag + `top_roles` projection (first 25).
**P1-4** Distinguishes `requests.Timeout` (kept as `unverified`) from `ConnectionError`/`HTTPError` (pruned); added `unverified` export column.
**P1-5** Narrowed MCP exception handling via `_EXPECTED` (warning) vs `Exception` (`log.exception`).
**P1-6** Added `_ok`/`_err` helpers with `default=str`; every tool return has a `status` field.
**P1-7** `create_profile` rejects empty name/titles and non-`.pdf` resume.
**P1-8** `get_results`/`export_report` now exclude `*_export.json` in the latest-sweep glob.
**P1-9** `get_results` clamps `limit` to `max(1, min(int(limit), 100))`.
**P1-10** Wizard salary parsing accepts `65000`, `65,000`, `$65,000`, `65k`; re-prompts on failure; rejects negatives.
**P1-11** Hybrid detection uses `\bhybrid\b` on title/location only.
**P1-12** Verified only — `custom` is already extracted from `platforms`; no failing case found, no change needed.

**P2-1** LICENSE handled by you (MIT); added a `## License` section referencing it.
**P2-2** Added `## Legal and responsible use` disclaimer.
**P2-3** Defined "playbook" in the README feature list.
**P2-4** Committed synthetic `docs/sample_report.pdf` + `docs/sample_report.png`; linked from README.
**P2-5** Pinned `requirements.txt` + added `requirements-dev.txt`; noted the Py3.13 pymupdf caveat.
**P2-6** Logs `Sweepy MCP starting; mcp=<ver> (module <path>)` to stderr at startup.
**P2-7** Audited link markup (renders as clickable annotations; XML-escaped `&`) and verified 4 cards/page (2 pages for 8 jobs).
**P2-8** Added 39 tests; ≥70% coverage on `swee.py` (85%), `server.py` (78%), `engine/scorer.py` (94%).
**P2-9** Added `.github/workflows/ci.yml` (3.10/3.11/3.12, ruff + pytest + coverage artifact).
**P2-10** Added `CHANGELOG.md` (Keep a Changelog; 1.5.0 entry mentions rebrand + MCP server).

## Tasks deferred

- **P1-2 fallback** (fire-and-return `_JOBS` + `sweep_status`): deferred — primary progress approach implemented; cannot reproduce a real-client timeout here.
- **P2-1 LICENSE file**: deferred to you (you are adding MIT directly).
- **P2-4/P2-7 live scraping**: replaced with synthetic fixtures per your instruction.
- **P1-12**: no change (verified non-issue).

## Verification output

- `grep -c "^def main" swee.py` → `1`
- `python swee.py --version` → exits 0 (`pymupdf MISSING` path covered by `test_get_dependency_versions_missing`)
- `python swee.py --setup` → wizard verified via `test_wizard_writes_remote_only_and_parses_salary` (`remote_only: true`); interactive run not exercised (curses)
- `python swee.py --profile ...` twice → two distinct file sets (timestamp test)
- server emits no human-readable stdout (no `print(` in `server.py`/`engine/`; stderr-only startup line)
- `grep -rn "^\s*print(" engine/` → empty; `server.py` → empty; `swee.py` → only the CLI banner in `main()` (documented exception)
- `grep -n "country_alice" engine/` → empty
- 200-URL validation → under 60s with mocked requests (order-preserving parallel test)
- zero-keyword job → score `0` (`test_zero_keyword_job_scores_zero`)
- `pytest -q` → `39 passed`
- `ruff check .` → `All checks passed!` (no unused imports / undefined names)
- MCP end-to-end / >2-min disconnect → not run against a real client; async progress verified with a fake `Context`

## Open questions for the maintainer

1. **License**: you are adding MIT from GitHub; the README `## License` section already references `LICENSE`.
2. **pandas pin**: pinned to `2.2.3` (not the dev venv's `3.0.6`) so the Python 3.10 CI matrix stays green — pandas 3.x requires 3.11+. Adjust if you drop 3.10.
3. **reportlab pin**: pinned to the installed `5.0.1`; if you prefer the long-stable line, use `4.x`.
4. **mcp pin**: pinned to `2.3.0`; the import shim still supports 1.x, but CI only exercises 2.x.

## Suggested commit messages (no commits made, per instruction)

`fix(P0-1): remove duplicate main` · `feat(P0-2): sandbox MCP write paths` · `refactor(P0-3): replace print with logging in engine` · `fix(P0-4): correct remote_only inversion` · `fix(P0-5): correct jobspy country kwarg` · `perf(P0-6): parallelize URL validation` · `fix(P0-7): remove score floor` · `fix(P0-8): timestamp report filenames` · `fix(P0-9): guard dependency lookup in --version` · `refactor(P0-10): remove redirect_stdout band-aid` · `fix(P0-11): log discovery failures per title` · `feat(P1-1): pipeline progress callbacks` · `feat(P1-2): wire progress through MCP tool` · `feat(P1-3): trim pipeline payload` · `feat(P1-4): distinguish timeout from dead-link` · `refactor(P1-5): narrow MCP exception handling` · `refactor(P1-6): consistent status on tool returns` · `feat(P1-7): validate create_profile inputs` · `fix(P1-8): exclude export files from get_results` · `fix(P1-9): clamp get_results limit` · `fix(P1-10): robust salary parsing` · `fix(P1-11): hybrid detection regex` · `test(P2-8): add unit test suite` · `chore(P2-5): pin dependencies` · `ci(P2-9): add GitHub Actions` · `docs(P2-2/P2-3/P2-4/P2-10): legal, playbook, demo, changelog`
