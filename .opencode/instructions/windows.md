# Windows and PowerShell 5.1

This workspace runs on Windows with PowerShell 5.1. The canonical files under
`.claude/` were written for a Unix-like shell, so translate their examples before
running them.

## Shell rules

- Use `python`, never `python3`. A `python3` command resolves to the Microsoft Store
  alias and fails or starts a different interpreter without the installed packages.
- Do not use `&&`, `||`, bash heredocs, `$(cat ...)`, or backtick continuations.
  Run dependent commands as `command1; if ($?) { command2 }`.
- Use `;` only for independent commands. Quote paths containing spaces with double
  quotes and prefer `-LiteralPath` for file cmdlets.
- Use the `read`, `write`, `edit`, `glob`, and `grep` tools for normal file work.
  Do not use `Get-Content` to read secrets, and do not use shell redirects to write
  repository files.
- To pass text to a Python stdin tool, use a PowerShell here-string:

  ```powershell
  @'
  text goes here
  '@ | python tools/posting_guard.py --text --json
  ```

- The repository root is the working directory. Do not `cd` permanently; if a tool
  needs another directory, use `Push-Location` and `Pop-Location`.

## Temporary files

Use `$env:TEMP\opencode-job-search` for fetched pages, cleaned postings, and batch
JSON. Never write fetched content, scratchpads, or intermediate results inside the
repository. `tools/fetch_page.py` refuses output paths inside the repository by
design.

## Bun and portal CLIs

There is no global Bun. Use the repository shim:

```powershell
& .opencode\bin\bun.cmd --version
& .opencode\bin\bun.cmd run .agents\skills\<portal>\cli\src\cli.ts <args>
```

Do not run `bun install`, `npm install`, or any package manager. The shipped portal
CLIs have no runtime dependencies.

## PDF toolchain

MiKTeX, `lualatex`, `xelatex`, `pdflatex`, and Poppler are not installed. Phase 1
does not compile or inspect PDFs. `/apply` must stop before its PDF step and report
the missing toolchain instead of claiming a check passed.

The `opencode.ps1` wrapper may print a PowerShell `NativeCommandError` trace before
normal output. This is cosmetic when the process exit code is still `0`; report the
actual exit code and do not treat the trace alone as a failure.
