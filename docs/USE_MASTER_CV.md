# Using `/apply --use-master-cv` — Original Resume Workflow

## Overview

The `--use-master-cv` flag lets you apply to jobs using your existing resume as-is, without generating tailored CVs, cover letters, or PDFs. The experience gate, fit evaluation, reviewer critique, and tracker recording still run — only the drafting and compilation steps are skipped.

## Prerequisites

1. **Your resume must be in `documents/cv/`** — this folder is Git-ignored (never committed).
2. **Exactly one resume file** must exist in `documents/cv/`. Supported extensions: `.pdf`, `.tex`, `.md`, `.txt`.
3. **Your resume must already be submission-ready** — preferably PDF. A `.tex` file is not submission-ready; compile it externally first if needed.
4. **No real personal data is read or processed during setup.** All tests use synthetic fixtures.

## Step-by-Step Instructions

### Step 1: Place your resume

Put your resume file in `documents/cv/`:

```
documents/cv/
└── your_resume.pdf          # or .tex, .md, .txt
```

This folder is Git-ignored — your personal data will never be committed.

### Step 2: Verify only one resume exists

`documents/cv/` must contain exactly one file:
- **Zero files** → you'll see: *"No resume found in documents/cv/. Place your CV there..."*
- **Multiple files** → you'll see: *"Multiple resumes found in documents/cv/: <list>. Remove all but one..."*

Remove extra files until only one remains.

### Step 3: Run the application workflow

```
/apply --use-master-cv https://example.com/job-posting
```

Or with pasted text:

```
/apply --use-master-cv
# then paste the posting text when prompted
```

The `--use-master-cv` flag may appear before or after the posting argument.

### Step 4: What happens next

The workflow runs these steps:

| Step | Action | Master CV Mode? |
|------|--------|-----------------|
| 0 | Experience gate (0–2 years) | ✅ Runs |
| 1 | Fit evaluation against your profile | ✅ Runs |
| 2 | CV tailoring | ⏭️ Skipped |
| 3 | Reviewer critique | ✅ Runs |
| 4 | Draft revision | ⏭️ Skipped |
| 5 | PDF compilation | ⏭️ Skipped |
| 6 | Verification checklist | ✅ Runs |
| 6b | Tracker recording | ✅ Runs |

### Step 5: Review output

You'll receive:
- Experience gate verdict (ELIGIBLE / INELIGIBLE / REVIEW)
- Fit evaluation results
- The path to your master CV under `documents/cv/`
- Reviewer findings
- An explicit note: *"PDF compilation not performed — original resume used as-is"*

### Step 6: Submit manually

The workflow does **not** submit, upload, email, or contact employers. You must:
1. Open your resume file from `documents/cv/`
2. Submit it externally through the employer's portal/application form
3. Record the outcome using `/outcome <company>` when you hear back

## Important Warnings

| Warning | Detail |
|---------|--------|
| Submission-ready format | Your resume must already be PDF (or another format the employer accepts). A `.tex` file is **not** submission-ready — compile externally first. |
| No cover letter | Master CV mode does not generate a cover letter. If the employer requires one, use the default `/apply` mode instead. |
| No PDF compilation | LaTeX (`lualatex`, `xelatex`, `pdflatex`) and Poppler are not run. If your resume is `.tex`, compile it yourself before submitting. |
| Experience gate still applies | Jobs requiring >2 years experience, or with missing/ambiguous experience requirements, will be blocked just like in default mode. |
| No automatic override | You cannot bypass the gate without explicitly requesting an override after seeing the gate reason. |

## Comparison: Default vs. Master CV Mode

| | Default `/apply` | `/apply --use-master-cv` |
|---|---|---|
| CV generation | Tailored per job | Uses existing resume as-is |
| Cover letter | Generated | Not generated |
| PDF compilation | Required (lualatex/xelatex) | Skipped |
| LaTeX/Poppler needed | Yes | No |
| Experience gate | ✅ | ✅ |
| Fit evaluation | ✅ | ✅ |
| Reviewer critique | ✅ | ✅ |
| Tracker recording | ✅ | ✅ |
| Manual submission | ✅ | ✅ |

## When to Use Each Mode

**Use default `/apply` when:**
- You want a tailored CV and cover letter for each job
- You have LaTeX installed and can compile PDFs
- The employer requires both CV and cover letter

**Use `/apply --use-master-cv` when:**
- You want to use your existing resume without tailoring
- You don't have LaTeX installed
- You only need to submit a single document (CV/resume)
- You want to apply quickly without drafting

## Privacy

- Your resume stays in `documents/cv/` — Git-ignored, never committed
- No personal data is copied into tracked files (`CLAUDE.md`, `.claude/skills/`, etc.)
- The resume file is never copied, renamed, or modified — byte-for-byte preserved
- All test fixtures are synthetic; no real resumes are processed

## Git-Ignore Protection

All candidate-specific paths are protected by `.gitignore`:

| Path | Rule |
|------|------|
| `documents/cv/**` | Line 74 |
| `documents/applications/**` | Line 82 |
| `job_search_tracker.csv` | Line 91 |
| `salary_data.json` | Line 23 |
| `company_research/*.json` | Line 112 |
| `**/job_scraper/seen_jobs.json` | Line 27 |

## Test Coverage

33 focused tests cover this workflow:

| Test Class | Tests |
|------------|-------|
| `OriginalResumeModeDocumented` | 10 |
| `MissingResumeStopsSafely` | 2 |
| `AmbiguousResumeStopsSafely` | 3 |
| `OriginalResumeModeSkipsGeneratedArtifacts` | 4 |
| `ExperienceGateStillApplies` | 5 |
| `CandidateFilesGitIgnored` | 6 |
| `DefaultApplyBehaviorUnchanged` | 3 |

All pass with the full suite (955 tests, 0 failures, 11 skipped).

---
