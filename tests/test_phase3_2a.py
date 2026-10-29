"""Focused tests for Phase 3.2A synthetic document generation.

Tests use synthetic data only and do not touch the real candidate profile.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PHASE3_DIR = REPO / "documents" / "phase3_test"
GENERATE_SCRIPT = REPO / "tools" / "generate_drafts_synthetic.py"
CV_OUTPUT = PHASE3_DIR / "cv_main_Junior_Backend_Developer.tex"
COVER_OUTPUT = PHASE3_DIR / "cover_letters_cover_Junior_Backend_Developer.tex"

JOB_ELIGIBLE = "We are looking for a Junior Backend Developer with 0-2 years of experience in Python."
JOB_REVIEW = "We are looking for a Junior Backend Developer with 1-3 years of experience in Python."
JOB_INELIGIBLE = "We are looking for a Senior Backend Developer with 5+ years of experience in Python."


def run_generator(job_text: str, title: str | None = None) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as td:
        profile = Path(td) / "profile.json"
        profile.write_text(
            json.dumps({
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "phone": "+1-555-123-4567",
                "linkedin": "https://linkedin.com/in/janedoe",
                "github": "https://github.com/janedoe",
                "degrees": ["Bachelor of Science in Computer Science"],
                "experience": [{
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "start": "2022",
                    "end": "Present",
                    "bullets": ["Built APIs", "Wrote tests"]
                }],
                "skills": ["Python", "Git", "Docker"]
            }),
            encoding="utf-8",
        )
        jd = Path(td) / "jd.txt"
        jd.write_text(job_text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT),
             "--profile", str(profile),
             "--job-description", str(jd),
             "--title", title or "Junior Backend Developer"],
            capture_output=True, text=True, encoding="utf-8",
        )


class Phase3GateTests(unittest.TestCase):
    """Test experience gate outcomes."""

    def test_eligible_generates_drafts(self):
        result = run_generator(JOB_ELIGIBLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ELIGIBLE", result.stdout)
        self.assertTrue(CV_OUTPUT.exists(), "CV draft should exist for eligible job")
        self.assertTrue(COVER_OUTPUT.exists(), "Cover letter draft should exist for eligible job")

    def test_review_blocks_generation(self):
        # Remove outputs first to ensure blocked run doesn't create them
        for p in (CV_OUTPUT, COVER_OUTPUT):
            if p.exists():
                p.unlink()
        result = run_generator(JOB_REVIEW, title="Junior Backend Developer")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("REVIEW", result.stdout)
        self.assertFalse(CV_OUTPUT.exists(), "No CV draft for REVIEW job")
        self.assertFalse(COVER_OUTPUT.exists(), "No cover-letter draft for REVIEW job")

    def test_ineligible_blocks_generation(self):
        for p in (CV_OUTPUT, COVER_OUTPUT):
            if p.exists():
                p.unlink()
        result = run_generator(JOB_INELIGIBLE, title="Senior Backend Developer")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("INELIGIBLE", result.stdout)
        self.assertFalse(CV_OUTPUT.exists(), "No CV draft for INELIGIBLE job")
        self.assertFalse(COVER_OUTPUT.exists(), "No cover-letter draft for INELIGIBLE job")


class Phase3PlaceholderTests(unittest.TestCase):
    """Test that generated drafts contain no unresolved placeholders."""

    def test_cv_no_placeholders(self):
        if not CV_OUTPUT.exists():
            run_generator(JOB_ELIGIBLE)
        self.assertTrue(CV_OUTPUT.exists())
        text = CV_OUTPUT.read_text(encoding="utf-8")
        # Check that key candidate data appears
        self.assertIn("Jane Doe", text)
        self.assertIn("jane.doe@example.com", text)
        self.assertIn("+1-555-123-4567", text)
        self.assertIn("Software Engineer", text)
        self.assertIn("Tech Corp", text)
        self.assertIn("Python", text)
        # No unresolved example tokens
        for tok in ["[First]", "[Last]", "[Your Address, City, Country]",
                    "[+XX XXXXXXXXXX]", "[your.email@example.com]",
                    "[Job Title]", "[Company]", "[YYYY-Present]",
                    "[Achievement or responsibility 1 - be specific, use numbers where possible]",
                    "[Skill Category 1]"]:
            self.assertNotIn(tok, text, f"Unresolved placeholder found: {tok}")

    def test_cover_no_placeholders(self):
        if not COVER_OUTPUT.exists():
            run_generator(JOB_ELIGIBLE)
        self.assertTrue(COVER_OUTPUT.exists())
        text = COVER_OUTPUT.read_text(encoding="utf-8")
        self.assertIn("Jane Doe", text)
        self.assertIn("Junior Backend Developer", text)
        self.assertIn("Tech Corp", text)
        self.assertIn("Python", text)
        for tok in ["[Last]", "[NAME]"]:
            self.assertNotIn(tok, text, f"Unresolved placeholder found: {tok}")


class Phase3PDFLibraryTests(unittest.TestCase):
    """Check available PDF libraries without installing anything."""

    def test_pypdf_available(self):
        try:
            import pypdf  # noqa: F401
            self.assertTrue(True, "pypdf is installed")
        except ImportError:
            self.fail("pypdf not available")

    def test_reportlab_available(self):
        try:
            import reportlab  # noqa: F401
            self.assertTrue(True, "reportlab is installed")
        except ImportError:
            self.fail("reportlab not available")


class Phase3LaTeXAvailabilityTests(unittest.TestCase):
    """Test LaTeX availability reporting when no TeX distribution is installed."""

    def test_latex_unavailable_reported_when_no_executable(self):
        """Generator should report LaTeX unavailability when no executable is on PATH."""
        result = run_generator(JOB_ELIGIBLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No LaTeX executable", result.stdout)
        self.assertIn("PDF compilation is unavailable", result.stdout)

    def test_no_pdf_generation_claim_without_latex(self):
        """Generator must not claim PDFs were generated or verified without LaTeX."""
        result = run_generator(JOB_ELIGIBLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("PDF compiled", result.stdout)
        self.assertNotIn("page-count verification", result.stdout)
        self.assertNotIn("layout verification succeeded", result.stdout)


if __name__ == "__main__":
    unittest.main()
