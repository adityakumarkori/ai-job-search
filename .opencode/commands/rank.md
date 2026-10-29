---
description: Triage scraped postings into a ranked shortlist using the canonical rank workflow
agent: build
model: opencode/deepseek-v4.1-flash-free
---

Read `.claude/commands/rank.md` and follow it exactly, except for the OpenCode and
Windows overrides below. `$ARGUMENTS` is the user's focus, `--all`, `--limit`, or
`--top` argument.

## OpenCode overrides

- Use `python`, never `python3`, for `tools/rank_state.py`, `tools/posting_guard.py`,
  `tools/experience_gate.py`, `tools/fetch_page.py`, and related tools.
- Dispatch only `posting-scorer` subagents with the `task` tool. Do not use `general`,
  `explore`, or nested subagents. Pass the job list and compact rubric inline; do not
  make the subagent read the profile files.
- Use `.opencode\bin\bun.cmd` for portal `detail` calls. Never install packages.
- Use `$env:TEMP\opencode-job-search` for the batch JSON file and fetched pages.
- Gate every fetched body with `tools/posting_guard.py` before scoring it. Use the
  cleaned text and preserve the verdict line.
- After the guard, gate the same posting with
  `python tools/experience_gate.py evaluate --in <fetched file> --title <title>`
  (add `--structured-min`, `--seniority`, and `--preserve <file>` when available).
  Put the returned object in that job's JSON as `"experience_gate"`. Do not score or
  rank without it; if the gate cannot run, return `"experience_gate": null` and let
  `rank_state.py` mark the job `REVIEW`.
- Never read the full `job_scraper/seen_jobs.json`; use the canonical state query and
  apply tools. `rank_state.py` persists the gate and keeps `REVIEW`/`INELIGIBLE` jobs
  out of `ranked` and `candidates`.
- Do not modify `job_search_tracker.csv` and do not apply to any job.
- Visible experience requirements still belong in the honest gaps list even when the
  gate is eligible or manually overridden.
- If a subagent tool is unavailable, score sequentially in the main context using the
  same rubric, guard, and experience-gate rules, and say that subagents were not used.

Finish with the canonical ranked shortlist, the `experience_blocked` jobs and their
gate reasons, excluded jobs, closing-soon and unreachable sections, and the state-update
result. Do not invent scores or deadlines. Never claim a blocked job was applied to.
