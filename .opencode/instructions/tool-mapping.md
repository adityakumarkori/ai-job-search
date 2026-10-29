# Claude-to-OpenCode Tool Mapping

Read the canonical workflow or agent file named by a wrapper, then apply this mapping.
Do not rewrite the canonical file.

| Canonical name | OpenCode tool |
|---|---|
| `Read` | `read` |
| `Write` | `write` |
| `Edit` | `edit` |
| `Bash` | `bash` |
| `Glob` | `glob` |
| `Grep` | `grep` |
| `WebFetch` | `webfetch` |
| `WebSearch` | `websearch` |
| `Agent` | `task` |
| `AskUserQuestion` | `question` |
| `Skill` | `skill` |
| `TodoWrite` | `todowrite` |

## Runtime differences

- The canonical `Agent` tool maps to `task`. Use only the subagent types configured
  for this project: `posting-fetcher`, `posting-scorer`, and `application-reviewer`.
  Do not use `general`, `explore`, or nested subagents.
- The canonical `AskUserQuestion` maps to `question`. Ask before any action that
  uploads, submits, sends, deletes, installs, or changes a remote.
- A subagent has no `write` or `edit` tool. Return proposed edits and research as
  text for the orchestrator to apply.
- The canonical files may mention `Claude`, `Claude Code`, or the `claude` CLI.
  Those references are upstream product text, not this runtime. Use `OpenCode` when
  a product name is needed; otherwise omit the name. Never claim Claude Code is
  running or that a Claude CLI command is available.
- Canonical code fences use `python3`, `${SCRATCHPAD}`, Unix pipes, and bash
  heredocs. Translate them using `windows.md`; use `python`, the temp directory
  described there, and a PowerShell here-string when stdin is required.
- Canonical command files use `$ARGUMENTS`. The wrapper substitutes the user's
  arguments before you act. Pass those arguments to the canonical workflow unchanged.
- The canonical posting-fetcher and posting-scorer use `${SCRATCHPAD:?}`. Set the
  scratchpad to `$env:TEMP\opencode-job-search` and use that path directly.

## Source of truth

- Workflows: `.claude/commands/<name>.md`
- Skills: `.claude/skills/<name>/SKILL.md` and their sibling files
- Agents: `.claude/agents/<name>.md`
- Portal CLIs: `.agents/skills/<portal>/cli/src/cli.ts`
- Candidate profile and scoring framework: `.claude/skills/job-application-assistant/`

Read only the files the current step needs. Do not bulk-read the backlog, the full
tracker, or every profile file.
