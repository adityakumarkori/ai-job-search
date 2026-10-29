# Search Queries for Job Scraper

<!-- India-focused Java/backend search set. Keep candidate-specific details in CLAUDE.md. -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search`; Danish demos and any skill you add with `/add-portal` are included the same way. You do **not** need a matching `site:` line below for those CLIs to run.

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

**Language scope:** write every query category in every language listed in your CLAUDE.md Languages table (typically 1-2, sometimes more). A posting requiring a language you have *not* declared, as a job condition, is excluded before scoring; a posting requiring a *higher level* than you declared in a language you *do* work in is flagged for your own judgment, not excluded — see `04-job-evaluation.md`'s Language Gate, the single source of truth for this rule. Translate each category's keywords rather than machine-translating word-for-word (e.g. "Frontend Developer" -> "Desarrollador Frontend", not a literal word-for-word translation) if you work in more than one language.

## Search Sites

Primary (India-focused boards and installed CLIs):
- **Naukri** (`naukri.com`) - largest general job board for India; use the WebSearch fallback unless a CLI exists
- **Indeed India** (`indeed.co.in`) - general job listings; useful for remote and hybrid filters
- **linkedin.com/jobs** - only when the user explicitly asks for LinkedIn, and only through `linkedin-search` when permitted; automated LinkedIn access is otherwise against its terms
- **Company career pages** - preferred for known product companies and startups

The installed portal CLIs remain primary for `/scrape`; these `site:` queries are the WebSearch fallback.

## Query Categories

Queries are grouped by priority and target India. Write **each category in every language from your Languages table** (see Language scope above). Add `remote` or `hybrid` where the board supports it; otherwise include India as the location.

**Organize by function, not job title.** Backend work is posted as "Java Backend Developer", "Backend Engineer", "Spring Boot Developer", "SDE 1 Backend", and similar titles. Use several variants rather than one exact title.

### Priority 1: Java / Backend Engineering

These match the strongest and most desired career direction.

```
site:naukri.com "Java Backend Developer" India
site:naukri.com "Backend Engineer" Java India
site:indeed.co.in "Java Backend Developer" remote India
site:indeed.co.in "Backend Engineer" Java hybrid India
site:naukri.com "Java Developer" Spring Boot India
```

### Priority 2: Spring Boot and Java Services

These match the core Java service-development stack.

```
site:naukri.com "Spring Boot Developer" India
site:naukri.com "Java Microservices" developer India
site:indeed.co.in "Spring Boot" backend engineer remote India
site:naukri.com "Java" "REST API" backend India
```

### Priority 3: Early-Career Backend Roles

Adjacent early-career titles with the same backend function.

```
site:naukri.com "Associate Backend Developer" India
site:naukri.com "SDE 1 Backend" India
site:indeed.co.in "Junior Java Developer" remote India
site:naukri.com "Software Engineer 1" Java India
```

### Priority 4: Broader Backend / Platform

Wider net for general backend and platform roles.

```
site:naukri.com "Backend Developer" Java India
site:indeed.co.in "Backend Developer" India remote
site:naukri.com "Software Engineer" backend Java India
site:indeed.co.in "Java Engineer" India hybrid
```

## Location Filter

When evaluating results, verify the job is in India and compatible with the user's work arrangement:
- India: remote or hybrid roles are acceptable
- Major tech hubs for onsite/hybrid: Bengaluru, Hyderabad, Pune, Chennai, Noida, Gurugram, Mumbai
- Outside India: excluded unless the posting is explicitly remote and open to candidates in India
- A posting with no clear location: include only if it is explicitly remote; flag the ambiguity

## Language Filter

Your working languages and levels are in CLAUDE.md's Languages table. When filtering scraped results, apply `04-job-evaluation.md`'s Language Gate: a posting requiring a language you haven't declared at all is excluded; a posting requiring a higher level than you declared in a language you do work in is not excluded, flag it clearly instead (see `job-scraper/SKILL.md`'s Step 3 "Quick Fit Assessment" for how the flag surfaces in `/scrape` output). Postings simply *written* in a language you don't work in, that don't require it on the job, are fine.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Experience Filter

Scraping may surface roles above the 0-2 year target; do not hide them. `/rank` runs
`tools/experience_gate.py` on every posting and keeps `REVIEW` or `INELIGIBLE` jobs out
of the shortlist with an honest reason. Missing experience text is never treated as
zero years.

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
