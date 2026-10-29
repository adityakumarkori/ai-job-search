#!/usr/bin/env python3
"""Synthetic CV and cover‑letter draft generator for Phase 3.2A.

Reads a synthetic profile JSON and a job description, runs the experience gate,
and, if ELIGIBLE, produces .tex drafts under documents/phase3_test/ using the
project's existing templates.  If REVIEW or INELIGIBLE the script aborts and
writes no draft files.

Safety:
 - Uses only the provided synthetic data.
 - Never reads the real 01-candidate-profile.md.
 - Exits cleanly (no document generation) when the gate says REVIEW or INELIGIBLE.
 - No network requests, no file writes outside documents/phase3_test/.
"""

import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to repository root)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
PHASE3_DIR = ROOT / "documents" / "phase3_test"
PROFILE_PATH = PHASE3_DIR / "synthetic_profile.json"
JOB_DESC_PATH = PHASE3_DIR / "job_description.txt"

CV_TEMPLATE_PATH = ROOT / "cv" / "main_example.tex"
COVER_TEMPLATE_PATH = ROOT / "cover_letters" / "cover.cls"

CV_OUTPUT_DIR = PHASE3_DIR
COVER_OUTPUT_DIR = PHASE3_DIR

EXPERIENCE_GATE = ROOT / "tools" / "experience_gate.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def last_from_name(name: str) -> str:
    return name.split()[-1] if name else "Doe"


def load_profile(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_job_description(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def run_experience_gate(text: str, title: str | None = None) -> dict:
    cmd = [sys.executable, str(EXPERIENCE_GATE), "evaluate", "--text", text]
    if title:
        cmd += ["--title", title]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"experience_gate failed: {result.stderr}")
    return json.loads(result.stdout.strip())


# ---------------------------------------------------------------------------
# CV template token replacements (moderncv)
# ---------------------------------------------------------------------------

def replace_cv_tokens(template: str, profile: dict) -> str:
    name = profile.get("name", "Jane Doe")
    email = profile.get("email", "jane.doe@example.com")
    phone = profile.get("phone", "+1-555-123-4567")
    linkedin = profile.get("linkedin", "https://linkedin.com/in/janedoe")
    github = profile.get("github", "https://github.com/janedoe")

    degree = profile.get("degrees", ["Bachelor of Science in Computer Science"])[0]
    exp = profile.get("experience", [{}])[0]
    exp_title = exp.get("title", "Software Engineer")
    exp_company = exp.get("company", "Tech Corp")
    exp_start = exp.get("start", "2022")
    exp_end = exp.get("end", "Present")
    exp_bullets = exp.get("bullets", ["Built APIs", "Wrote tests"])
    skills = profile.get("skills", ["Python", "Git", "Docker"])

    replacements = [
        # Personal data
        (r"\name{[First]}{[Last]}", f"\\name{{{name}}}{{{last_from_name(name)}}}"),
        (r"pdftitle={[YOUR_NAME] - CV}", f"pdftitle={{{name} - CV}}"),
        (r"\address{[Your Address, City, Country]}{}{}", "\\address{Synthetic City, Synthetic Country}{}{}"),
        (r"\phone[mobile]{[+XX XXXXXXXXXX]}", f"\\phone[mobile]{{{phone}}}"),
        (r"\email{[your.email@example.com]}", f"\\email{{{email}}}"),
        (
            r"\extrainfo{\href{[https://linkedin.com/in/your-profile]}{LinkedIn}, \href{[https://github.com/your-username]}{GitHub}}",
            f"\\extrainfo{{\\href{{{linkedin}}}{{LinkedIn}}, \\href{{{github}}}{{GitHub}}}}",
        ),
        # Education tokens
        (r"\cventry{[YYYY-YYYY]}", "\\cventry{2020-2024}"),
        (r"[Degree] in [Field]", f"{degree}"),
        (r"[Institution]", "Synthetic University"),
        (r"[City, Country]", "Synthetic City, Synthetic Country"),
        (r"[Thesis Title]", "Synthetic Thesis"),
        (r"[Brief description of research focus.]", "[Brief description of research focus.]"),
        (r"[Brief description or key topics.]", "[Synthetic key topics.]"),
        # Experience tokens
        (r"\cventry{[YYYY-Present]}", f"\\cventry{{{exp_start}-{exp_end}}}"),
        (r"[Job Title]", f"{exp_title}"),
        (r"[Company]", f"{exp_company}"),
        (r"[Achievement or responsibility 1 - be specific, use numbers where possible]",
         f"{exp_bullets[0] if len(exp_bullets) > 0 else 'Built APIs'}"),
        (r"[Achievement or responsibility 2]",
         f"{exp_bullets[1] if len(exp_bullets) > 1 else 'Wrote tests'}"),
        (r"[Achievement or responsibility 3]",
         f"{exp_bullets[2] if len(exp_bullets) > 2 else 'Reviewed code'}"),
        (r"[Achievement or responsibility 4]",
         f"{exp_bullets[3] if len(exp_bullets) > 3 else 'Participated in code reviews'}"),
        (r"\item {[Achievement or responsibility 1]}",
         f"{exp_bullets[0] if len(exp_bullets) > 0 else 'Built APIs'}"),
        # Skills tokens
        (r"\item \textbf{[Skill Category 1]}: [Specific skills, frameworks, tools. Be concrete.]",
         f"\\item \\textbf{{{skills[0] if len(skills) > 0 else 'Python'}}}: {', '.join(skills[:3])}"),
        (r"\item \textbf{[Skill Category 2]}: [Specific skills, frameworks, tools.]",
         f"\\item \\textbf{{{skills[1] if len(skills) > 1 else 'Git'}}}: Version control and collaboration"),
        (r"\item \textbf{[Skill Category 3]}: [Specific skills, frameworks, tools.]",
         f"\\item \\textbf{{{skills[2] if len(skills) > 2 else 'Docker'}}}: Containerisation and deployment"),
        (r"\item \textbf{[Skill Category 4]}: [Domain expertise, methods, approaches.]",
         r"\item \textbf{Synthetic domain expertise}: REST APIs, microservices"),
        (r"\item \textbf{[Skill Category 5]}: [Tools, platforms, software.]",
         r"\item \textbf{Synthetic tools}: Linux, CI/CD pipelines"),
        # Language placeholders
        (r"[Language 1] (native), [Language 2] (fluent), [Language 3] (intermediate).",
         "Synthetic Language 1 (native), Synthetic Language 2 (fluent)."),
        # Publication placeholders
        (r"[Author(s)]", "Synthetic Author"),
        (r"\([Year]\)", "(2024)"),
        (r"[Title]", "Synthetic Title"),
        (r"[Journal/Conference]", "Synthetic Journal"),
        (r"\href{[DOI_URL]}{DOI link}", "\\href{https://example.com}{DOI link}"),
        # Honors placeholders
        (r"[Award Name]", "Synthetic Award"),
        (r"[Event/Organization]", "Synthetic Event"),
        (r"\([Year]\)\.}", "(2024).}"),
    ]

    for old, new in replacements:
        if old in template:
            template = template.replace(old, new)
        else:
            # Non-fatal: some tokens may be formatted differently in the template.
            pass

    return template


# ---------------------------------------------------------------------------
# Cover letter template token replacements
# ---------------------------------------------------------------------------

def replace_cover_tokens(template: str, profile: dict, job_title: str, company: str) -> str:
    """Generate a cover letter document using the cover.cls class.

    cover.cls is a class file (not a document template), so we build a
    minimal .tex document that loads it and fills in the commands.
    """
    name = profile.get("name", "Jane Doe")
    last_name = last_from_name(name)
    skills = profile.get("skills", ["Python", "Git", "Docker"])

    body = (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to express my strong interest in the {job_title} position at {company}. "
        f"With my background in {', '.join(skills[:3])} and my experience in backend development, "
        f"I am confident that I can contribute effectively to your team.\n\n"
        f"Throughout my career, I have built APIs and participated in code reviews. "
        f"My technical skills include {', '.join(skills[:3])}. I am particularly drawn to {company} "
        f"because of its reputation for innovation.\n\n"
        f"Thank you for considering my application. I look forward to the opportunity "
        f"to discuss how my experience aligns with the goals of {company}.\n\n"
        f"Sincerely,\n{name}"
    )

    doc = (
        "\\documentclass{cover}\n"
        "\\begin{document}\n"
        f"\\namesection{{{name}}}{{{last_name}}}{{Synthetic Candidate}}\n"
        f"\\companyname{{{company}}}\n"
        f"\\companyaddress{{Synthetic City, Synthetic Country}}\n"
        f"\\currentdate{{October 2026}}\n"
        f"\\lettercontent{{{body}}}\n"
        f"\\closing{{Sincerely}}\n"
        f"\\signature{{{name}}}\n"
        "\\end{document}\n"
    )
    return doc


# ---------------------------------------------------------------------------
# Placeholder validation
# ---------------------------------------------------------------------------

def check_no_original_candidate_info(text: str) -> list[str]:
    example_tokens = [
        "[First]", "[Last]", "[Your Address, City, Country]",
        "[+XX XXXXXXXXXX]", "[your.email@example.com]",
        "[https://linkedin.com/in/your-profile]",
        "[https://github.com/your-username]", "[YOUR_NAME]",
        "[YYYY-YYYY]", "[Degree] in [Field]", "[Institution]", "[City, Country]",
        "[YYYY-Present]", "[Job Title]", "[Company]",
        "[Achievement or responsibility 1 - be specific, use numbers where possible]",
        "[Achievement or responsibility 2]",
        "[Achievement or responsibility 3]",
        "[Achievement or responsibility 4]",
        "[Skill Category 1]: [Specific skills, frameworks, tools. Be concrete.]",
        "[Skill Category 2]: [Specific skills, frameworks, tools.]",
        "[Skill Category 3]: [Specific skills, frameworks, tools.]",
        "[Skill Category 4]: [Domain expertise, methods, approaches.]",
        "[Skill Category 5]: [Tools, platforms, software.]",
        "[Language 1] (native), [Language 2] (fluent), [Language 3] (intermediate).",
        "[Author(s)] ([Year]). [Title]. [Journal/Conference]. \\href{[DOI_URL]}{DOI link}",
        "[Award Name]", "[Event/Organization]",
    ]
    found = []
    for tok in example_tokens:
        if tok in text:
            found.append(tok)
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------------------
# Main generation workflow
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Synthetic CV & cover-letter draft generator (Phase 3.2A)."
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=PHASE3_DIR / "synthetic_profile.json",
        help="Path to synthetic profile JSON.",
    )
    parser.add_argument(
        "--job-description",
        type=Path,
        default=PHASE3_DIR / "job_description.txt",
        help="Path to synthetic job description text.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional job title for the experience gate.",
    )
    args = parser.parse_args(argv)

    # 1. Load data
    profile = load_profile(args.profile)
    job_description = load_job_description(args.job_description)

    # 2. Run experience gate
    gate = run_experience_gate(job_description, title=args.title)
    verdict = gate.get("verdict", "UNKNOWN")
    reason = gate.get("reason", "no reason")

    print(f"Experience gate verdict: {verdict} ({reason})")

    # 2a. ELIGIBLE -> generate drafts
    if verdict == "ELIGIBLE":
        cv_template = CV_TEMPLATE_PATH.read_text(encoding="utf-8")
        cover_template = COVER_TEMPLATE_PATH.read_text(encoding="utf-8")

        cv_content = replace_cv_tokens(cv_template, profile)
        leftover_cv = check_no_original_candidate_info(cv_content)
        if leftover_cv:
            print(f"WARNING: CV still contains original example info: {leftover_cv}")

        cv_path = CV_OUTPUT_DIR / "cv_main_Junior_Backend_Developer.tex"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(cv_content, encoding="utf-8")
        print(f"CV draft written to {cv_path}")

        cover_content = replace_cover_tokens(cover_template, profile, "Junior Backend Developer", "Tech Corp")
        leftover_cover = check_no_original_candidate_info(cover_content)
        if leftover_cover:
            print(f"WARNING: Cover letter still contains original example info: {leftover_cover}")

        cover_path = COVER_OUTPUT_DIR / "cover_letters_cover_Junior_Backend_Developer.tex"
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.write_text(cover_content, encoding="utf-8")
        print(f"Cover-letter draft written to {cover_path}")

        print(
            "\nDrafts generated under documents/phase3_test/ (git-ignored). "
            "Compile with lualatex/xelatex when a LaTeX distribution is available."
        )
    else:
        # REVIEW or INELIGIBLE -> abort, no docs
        print(
            f"Job not eligible for application (gate verdict: {verdict}, reason: {reason}). "
            "Document generation aborted."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
