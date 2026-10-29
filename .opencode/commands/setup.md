---
description: Guarded profile onboarding using the canonical /setup workflow
agent: build
model: opencode/deepseek-v4.1-flash-free
---

Read `.claude/commands/setup.md` and follow it exactly, except for the OpenCode and
Windows overrides below. `$ARGUMENTS` is the user's setup argument (for example
`--section identity`).

## Mandatory privacy preflight

1. Run `git remote get-url origin`. If it fails, there is no `origin`; do not treat
   that as proof the repository is private.
2. Do not run `gh`. If an origin exists, visibility is unknown unless the user states
   it. Treat a public fork or unknown visibility as unsafe.
3. Explain that setup writes personal data into tracked files (`CLAUDE.md`,
   `.claude/skills/job-application-assistant/01-07`, `cv/main_example.tex`, and
   `.claude/skills/job-scraper/search-queries.md`). No profile write may happen until
   the user explicitly confirms they understand and want to proceed.
4. If the user does not confirm, stop without writing anything. This is the expected
   Phase 1 behavior.
5. Never copy documents into tracked files. `documents/` stays a local source.

## OpenCode overrides

- Use `read`, `glob`, `grep`, `edit`, `write`, `bash`, and `question`, not Claude tool
  names. Use `python`, never `python3`.
- Use `.opencode\bin\bun.cmd` if a workflow step needs Bun; do not run package managers.
- Scan `documents/**/*` with `glob` and report counts per subfolder. Do not read the
  documents until the user chooses Path A and confirms the privacy preflight.
- Do not claim Claude Code is running. If a product name is needed, say OpenCode.
- Do not send, upload, or submit anything. Do not run `/gmail-sync` or `/notion-sync`.
- Do not edit canonical commands, agents, settings, or skill definitions.

Only after explicit confirmation, follow the canonical paths and write the confirmed
profile changes with targeted edits. Finish with the canonical confirmation summary.
