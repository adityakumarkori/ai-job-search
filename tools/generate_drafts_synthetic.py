#!/usr/bin/env python3
"""Synthetic CV and cover‑letter draft generator for Phase 3.1 testing.

Reads a synthetic profile JSON and a job description, runs the experience gate,
and, if eligible, produces .tex drafts under documents/phase3_test/ using the
project's existing templates.

Safety:
 - Uses only the provided synthetic data.
 - Never reads the real 01‑candidate‑profile.md.
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
# Helper: last word of a name (for cover‑letter placeholder)
# ---------------------------------------------------------------------------

def last_from_name(name: str) -> str:
    return name.split()[-1] if name else "Doe"


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_profile(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_job_description(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Experience gate
# ---------------------------------------------------------------------------

def run_experience_gate(text: str, title: str | None = None) -> dict:
    cmd = [sys.executable, str(EXPERIENCE_GATE), "evaluate", "--text", text]
    if title:
        cmd += ["--title", title]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"experience_gate failed: {result.stderr}")
    return json.loads(result.stdout.strip())


# ---------------------------------------------------------------------------
# Template placeholders replacement (simple string based, no regex)
# ---------------------------------------------------------------------------

def replace_cv_personal(template: str, profile: dict) -> str:
    """Replace the four personal‑data lines in the moderncv template.

    The template contains exactly these word‑for‑word strings (as they appear
    in the shipped file).  We replace them with the synthetic values.
    """
    name = profile.get("name", "Jane Doe")
    email = profile.get("email", "jane.doe@example.com")
    phone = profile.get("phone", "+1-555-123-4567")
    linkedin = profile.get("linkedin", "https://linkedin.com/in/janedoe")
    github = profile.get("github", "https://github.com/janedoe")

    # 1) \name{[First]}{[Last]}
    tmpl_name = r"\name{[First]}{[Last]}"
    tmpl_name_repl = f"\\name{{{name}}}{{{last_from_name(name)}}}"
    template = template.replace(tmpl_name, tmpl_name_repl)

    # 2) \phone[mobile]{[+XX XXXXXXXXXX]}
    tmpl_phone = r"\phone[mobile]{[+XX XXXXXXXXXX]}"
    tmpl_phone_repl = f"\\phone[mobile]{{{phone}}}"
    template = template.replace(tmpl_phone, tmpl_phone_repl)

    # 3) \email{[your.email@example.com]}
    tmpl_email = r"\email{[your.email@example.com]}"
    tmpl_email_repl = f"\\email{{{email}}}"
    template = template.replace(tmpl_email, tmpl_email_repl)

    # 4) \extrainfo{{LinkedIn: [https://linkedin.com/in/your-profile], GitHub: [https://github.com/your-username]}}
    tmpl_extrainfo = (
        r"\extrainfo{{LinkedIn: [https://linkedin.com/in/your-profile], GitHub: [https://github.com/your-username]}}"
    )
    tmpl_extinfo_repl = (
        f"\\extrainfo{{LinkedIn: {linkedin}, GitHub: {github}}}"
    )
    template = template.replace(tmpl_extrainfo, tmpl_extinfo_repl)

    return template


def replace_cover_personal(template: str, profile: dict) -> str:
    """Replace the \\name line in cover.cls.

    The template has \\name{{NAME}}{{[Last]}}.
    """
    name = profile.get("name", "Jane Doe")
    last_name = last_from_name(name)
    # First replace {NAME}
    template = template.replace("{NAME}", name)
    # Then replace the [Last] placeholder (appears as [Last] inside the second braces)
    template = template.replace("[Last]", last_name)
    return template


# ---------------------------------------------------------------------------
# Gate‑driven generation
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Synthetic CV & cover‑letter draft generator (Phase 3.1)."
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

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    profile = load_profile(args.profile)
    job_description = load_job_description(args.job_description)

    # ------------------------------------------------------------------
    # 2. Run experience gate
    # ------------------------------------------------------------------
    gate = run_experience_gate(job_description, title=args.title)
    verdict = gate.get("verdict", "UNKNOWN")
    reason = gate.get("reason", "no reason")

    print(f"Experience gate verdict: {verdict} ({reason})")

    # ------------------------------------------------------------------
    # 2a. ELIGIBLE → generate drafts
    # ------------------------------------------------------------------
    if verdict == "ELIGIBLE":
        # ---- CV template ----
        cv_template = CV_TEMPLATE_PATH.read_text(encoding="utf-8")
        cv_content = replace_cv_personal(cv_template, profile)

        cv_path = CV_OUTPUT_DIR / f"cv_main_Junior_Backend_Developer.tex"
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(cv_content, encoding="utf-8")
        print(f"CV draft written to {cv_path}")

        # ---- Cover letter template ----
        cover_template = COVER_TEMPLATE_PATH.read_text(encoding="utf-8")
        cover_content = replace_cover_personal(cover_template, profile)

        cover_path = COVER_OUTPUT_DIR / f"cover_letters_cover_Junior_Backend_Developer.tex"
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.write_text(cover_content, encoding="utf-8")
        print(f"Cover‑letter draft written to {cover_path}")

        print(
            "\nDrafts generated under documents/phase3_test/ (git‑ignored). "
            "Compile with lualatex/xelatex when a LaTeX distribution is available."
        )
    else:
        # REVIEW or INELIGIBLE → abort, no docs
        print(
            f"Job not eligible for application (gate verdict: {verdict}, reason: {reason}). "
            "Document generation aborted."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()