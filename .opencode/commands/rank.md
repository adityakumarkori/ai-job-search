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
  `tools/fetch_page.py`, and related tools.
- Dispatch only `posting-scorer` subagents with the `task` tool. Do not use `general`,
  `explore`, or nested subagents. Pass the job list and compact rubric inline; do not
  make the subagent read the profile files.
- Use `.opencode\bin\bun.cmd` for portal `detail` calls. Never install packages.
- Use `$env:TEMP\opencode-job-search` for the batch JSON file and fetched pages.
- Gate every fetched body with `tools/posting_guard.py` before scoring it. Use the
  cleaned text and preserve the verdict line.
- Never read the full `job_scraper/seen_jobs.json`; use the canonical state query and
  apply tools.
- Do not modify `job_search_tracker.csv` and do not apply to any job.
- The strict 0-2 experience gate is Phase 2 and is not implemented. Do not claim it
  ran. Visible experience requirements still belong in the honest gaps list.
- If a subagent tool is unavailable, score sequentially in the main context using the
  same rubric and guard rules, and say that subagents were not used.

Finish with the canonical ranked shortlist, excluded jobs, closing-soon and
unreachable sections, and the state-update result. Do not invent scores or deadlines.
