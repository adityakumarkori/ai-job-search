---
description: Generate the local application dashboard using the canonical html-report workflow
agent: build
model: opencode/deepseek-v4.1-flash-free
---

Read `.claude/commands/html-report.md` and follow it exactly, except for the OpenCode
and Windows overrides below. `$ARGUMENTS` is an optional output path.

## OpenCode overrides

- The default output is `reports/application-dashboard.html`; create `reports/` if
  needed. Accept an explicit alternative path from `$ARGUMENTS`.
- Write one self-contained local HTML file with `write`; do not start a server, open a
  browser, or publish the file.
- Use the upstream dashboard structure, escaping rules, and SVG charts. Replace the
  footer text with `Generated with OpenCode · ai-job-search · {ISO date}`. Do not claim
  Claude Code generated it.
- Read only `job_search_tracker.csv` and the application archives needed for the
  report. Do not read the full `job_scraper/seen_jobs.json`.
- Use `python`, never `python3`, for any date or aggregation helper. Use PowerShell
  only for read-only checks.
- Do not modify the tracker, archives, or any skill file. The report is data-only.
- Do not upload, send, or share the report. It stays local.

Finish with the output path, the source rows and archives counted, and any sections
that had to be omitted for lack of data. Do not invent statistics.
