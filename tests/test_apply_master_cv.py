"""Guards for /apply --use-master-cv: original-resume application path.

Tests use synthetic data only and never read or process a real resume.
The OpenCode apply command wrapper lives at .opencode/commands/apply.md;
the canonical Claude spec at .claude/commands/apply.md is unchanged.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APPLY_WRAPPER = REPO / ".opencode" / "commands" / "apply.md"
GITIGNORE = REPO / ".gitignore"


def section(path, heading):
    """The body of one markdown section, up to the next heading of any depth."""
    text = path.read_text(encoding="utf-8")
    start = text.index(heading) + len(heading)
    rest = text[start:]
    end = re.search(r"^#{1,4} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def normalized(text: str) -> str:
    """Collapse whitespace so line-wrapped phrases still match."""
    return " ".join(text.split())


class OriginalResumeModeDocumented(unittest.TestCase):
    """The --use-master-cv option must be documented in the apply wrapper."""

    def setUp(self):
        self.text = APPLY_WRAPPER.read_text(encoding="utf-8")

    def test_use_master_cv_flag_is_documented(self):
        self.assertIn("--use-master-cv", self.text)

    def test_master_cv_mode_uses_documents_cv(self):
        self.assertIn("documents/cv/", self.text)

    def test_master_cv_mode_skips_tailoring(self):
        self.assertIn("Skip CV tailoring", self.text)

    def test_master_cv_mode_skips_cover_letter(self):
        self.assertIn("cover-letter generation", self.text)

    def test_master_cv_mode_skips_compilation(self):
        self.assertIn("PDF compilation", self.text)
        self.assertIn("Step 5", self.text)

    def test_master_cv_file_is_not_modified(self):
        self.assertIn("never copied, renamed, or modified", self.text)
        self.assertIn("byte-for-byte", self.text)

    def test_master_cv_submission_ready_warning(self):
        normalized_text = normalized(self.text)
        self.assertIn("submission-ready format", normalized_text)
        self.assertIn("not a submission-ready PDF", normalized_text)

    def test_master_cv_no_latex_poppler(self):
        self.assertIn("Do not run LaTeX or Poppler", self.text)

    def test_master_cv_experience_gate_still_applies(self):
        self.assertIn("experience gate", self.text)

    def test_master_cv_tracker_recording_still_applies(self):
        self.assertIn("tracker recording", self.text)


class MissingResumeStopsSafely(unittest.TestCase):
    """Zero resumes in documents/cv/ must produce a clear error."""

    def setUp(self):
        self.step = section(APPLY_WRAPPER, "## Original-resume mode (`--use-master-cv`)")

    def test_zero_resumes_produces_clear_error(self):
        self.assertIn("No resume found in documents/cv/", self.step)

    def test_zero_resumes_tells_user_what_to_do(self):
        self.assertIn("Place your CV there", normalized(self.step))
        self.assertIn("re-run /apply --use-master-cv", self.step)


class AmbiguousResumeStopsSafely(unittest.TestCase):
    """Multiple resumes in documents/cv/ must stop without choosing."""

    def setUp(self):
        self.step = section(APPLY_WRAPPER, "## Original-resume mode (`--use-master-cv`)")

    def test_multiple_resumes_produces_clear_error(self):
        self.assertIn("Multiple resumes found in documents/cv/", normalized(self.step))

    def test_multiple_resumes_lists_files(self):
        self.assertIn("<list>", self.step)

    def test_multiple_resumes_tells_user_to_remove_extra(self):
        self.assertIn("Remove all but one", self.step)


class OriginalResumeModeSkipsGeneratedArtifacts(unittest.TestCase):
    """Master CV mode must not generate tailored CV, cover letter, or PDF."""

    def setUp(self):
        self.step = section(APPLY_WRAPPER, "## Original-resume mode (`--use-master-cv`)")

    def test_skips_cv_tailoring(self):
        self.assertIn("Skip CV tailoring (Step 2 drafting)", self.step)

    def test_skips_cover_letter_generation(self):
        self.assertIn("cover-letter generation", self.step)

    def test_skips_pdf_compilation(self):
        self.assertIn("PDF compilation", normalized(self.step))
        self.assertIn("Step 5", self.step)

    def test_master_cv_is_application_document(self):
        self.assertIn("The master CV is the application document", self.step)


class ExperienceGateStillApplies(unittest.TestCase):
    """The 0-2 experience gate must not be bypassed in master CV mode."""

    def setUp(self):
        self.text = APPLY_WRAPPER.read_text(encoding="utf-8")

    def test_experience_gate_runs_before_drafting(self):
        self.assertIn("experience gate (Step 0)", self.text)

    def test_ineligible_jobs_blocked(self):
        self.assertIn("INELIGIBLE", self.text)

    def test_review_jobs_blocked(self):
        self.assertIn("REVIEW", self.text)

    def test_no_automatic_override(self):
        normalized_text = normalized(self.text)
        self.assertIn("Do not override on your own", normalized_text)


class CandidateFilesGitIgnored(unittest.TestCase):
    """Candidate-specific files must remain untracked by Git."""

    def setUp(self):
        self.text = GITIGNORE.read_text(encoding="utf-8")

    def test_documents_cv_is_ignored(self):
        self.assertIn("documents/cv/**", self.text)

    def test_documents_applications_is_ignored(self):
        self.assertIn("documents/applications/**", self.text)

    def test_tracker_is_ignored(self):
        self.assertIn("job_search_tracker.csv", self.text)

    def test_salary_data_is_ignored(self):
        self.assertIn("salary_data.json", self.text)

    def test_company_research_is_ignored(self):
        self.assertIn("company_research/*.json", self.text)

    def test_job_scraper_seen_jobs_is_ignored(self):
        self.assertIn("**/job_scraper/seen_jobs.json", self.text)


class DefaultApplyBehaviorUnchanged(unittest.TestCase):
    """The default /apply path (without --use-master-cv) must be unaffected."""

    def setUp(self):
        self.text = APPLY_WRAPPER.read_text(encoding="utf-8")

    def test_default_path_still_drafts_tailored_cv(self):
        self.assertIn("draft a tailored CV and cover letter", self.text)

    def test_default_path_still_checks_latex(self):
        self.assertIn("lualatex", self.text)
        self.assertIn("xelatex", self.text)
        self.assertIn("pdflatex", self.text)

    def test_default_path_still_reports_pdf_not_run(self):
        normalized_text = normalized(self.text)
        self.assertIn("PDF compilation", normalized_text)
        self.assertIn("not run", normalized_text)

    def test_canonical_apply_unchanged(self):
        canonical = REPO / ".claude" / "commands" / "apply.md"
        self.assertTrue(canonical.is_file(), "canonical apply.md must still exist")


if __name__ == "__main__":
    unittest.main()
