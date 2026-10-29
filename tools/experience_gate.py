#!/usr/bin/env python3
"""Deterministic 0-2 years experience gate for job postings.

The gate combines FreeHire's structured `enrichment.experience_years_min` with
an exact, auditable parse of the posting text. It never guesses: missing,
ambiguous, conflicting, or adversarial evidence is REVIEW, never ELIGIBLE.
Only an explicit minimum of two years or less can be ELIGIBLE.

Usage:
  python tools/experience_gate.py evaluate [--in FILE | --text TEXT]
  python tools/experience_gate.py check (--key KEY | --url URL)
  python tools/experience_gate.py record --key KEY [--in FILE | --text TEXT]
  python tools/experience_gate.py override (--key KEY | --url URL) --reason TEXT --confirm

`evaluate` prints JSON and does not write state. `check` reports whether the
stored verdict permits /apply. `override` writes an explicit, reasoned manual
override; it never rewrites the gate verdict. Exit 0 for parsed output, 2 for
bad input/state, and 1 for a refused write operation.
"""

import argparse
import hashlib
import html
import json
import math
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "job_scraper" / "seen_jobs.json"
PARSER_VERSION = "1.0.0"
VERDICTS = ("ELIGIBLE", "INELIGIBLE", "REVIEW")
SOURCES = ("structured", "description", "structured+description", "none")
MAX_EXPERIENCE = 2.0

NUMBER = r"(?:\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
SEP = r"(?:-|\u2010|\u2011|\u2012|\u2013|\u2014|\u2015|\u2212|to|through)"
YEARS = r"(?:years?|yrs?)"
YEAR_RE = re.compile(
    rf"(?P<low>{NUMBER})(?:\s*{SEP}\s*(?P<high>{NUMBER}))?"
    rf"(?P<plus>\s*\+|\s*(?:or\s+more|or\s+greater|and\s+above))?"
    rf"\s*{YEARS}\b(?P<after>\s*(?:\+|or\s+more|or\s+greater|and\s+above|plus))?",
    re.IGNORECASE,
)
WORD_VALUES = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
}
FRESHER_RE = re.compile(
    r"\b(?:fresher|freshers|fresh\s+graduat(?:e|es)|"
    r"no\s+(?:prior\s+)?(?:work\s+)?experience\s+(?:is\s+)?(?:required|necessary|needed)|"
    r"experience\s+not\s+required|zero\s+(?:years?|yrs?)(?:\s+of)?\s+experience)\b",
    re.IGNORECASE,
)
OPEN_PREFIX_RE = re.compile(
    r"\b(?:at\s+least|minimum(?:\s+of)?|min\.?|no\s+less\s+than|not\s+less\s+than|"
    r"over|more\s+than|greater\s+than)\s*$",
    re.IGNORECASE,
)
MAX_PREFIX_RE = re.compile(
    r"\b(?:at\s+most|maximum(?:\s+of)?|max(?:imum)?\.?(?:\s+of)?|up\s+to|"
    r"no\s+more\s+than|not\s+more\s+than|less\s+than|under|below)\s*$",
    re.IGNORECASE,
)
OPEN_SUFFIX_RE = re.compile(
    r"^\s*(?:or\s+more|or\s+greater|and\s+above|minimum|min\.?|plus|\+)\b",
    re.IGNORECASE,
)
MAX_SUFFIX_RE = re.compile(
    r"^\s*(?:or\s+less|or\s+fewer|or\s+below|max(?:imum)?)\b",
    re.IGNORECASE,
)
OPTIONAL_RE = re.compile(
    r"\b(?:preferred|nice\s+to\s+have|good\s+to\s+have|bonus|desirable|advantage|"
    r"optional|ideally|is\s+a\s+plus|a\s+plus)\b",
    re.IGNORECASE,
)
ADVERSARIAL_RE = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions|"
    r"system\s+prompt|you\s+are\s+(?:an?\s+)?(?:ai|assistant|model)|"
    r"</?\s*(?:script|iframe)\b|javascript\s*:|data\s*:\s*text/html",
    re.IGNORECASE,
)
SENIOR_RE = re.compile(r"\b(?:senior|sr\.?|lead|principal|staff|architect|manager)\b", re.IGNORECASE)
SENIORITY_SENIOR_RE = re.compile(r"\b(?:senior|sr\.?|lead|principal|staff|manager|architect)\b", re.IGNORECASE)
INVISIBLE_RE = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f"
    "\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff"
    "\U000E0000-\U000E007F]"
)


class GateError(Exception):
    pass


def _number(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in WORD_VALUES:
        return WORD_VALUES[text]
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _clean_number(value):
    if value is None:
        return None
    return int(value) if float(value).is_integer() else float(value)


def _iso(value=None):
    if value is None:
        moment = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise GateError(f"invalid --now value: {value}") from exc
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_text(raw):
    text = str(raw or "").replace("\r\n", "\n").replace("\r", "\n")
    text = html.unescape(text)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</?[A-Za-z][^>]{0,300}>", " ", text)
    text = INVISIBLE_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _snippet(text, start, end, span=70):
    left = max(0, start - span)
    right = min(len(text), end + span)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def _evidence(text, match, source="description", extra=None):
    item = {
        "source": source,
        "text": _snippet(text, match.start(), match.end()),
        "start": match.start(),
        "end": match.end(),
    }
    if extra:
        item.update(extra)
    return item


def _constraint(kind, low=None, high=None, optional=False, evidence=None, **extra):
    item = {"kind": kind, "low": low, "high": high, "optional": optional, "evidence": evidence}
    item.update(extra)
    return item


def _parse_constraints(text):
    constraints = []
    for match in YEAR_RE.finditer(text):
        low = _number(match.group("low"))
        high = _number(match.group("high"))
        if low is None or (match.group("high") is not None and high is None):
            constraints.append(
                _constraint("invalid", evidence=_evidence(text, match), reason="unreadable number")
            )
            continue

        prefix = text[max(0, match.start() - 48):match.start()]
        suffix = text[match.end():match.end() + 48]
        plus = bool(match.group("plus") or match.group("after"))
        optional = bool(OPTIONAL_RE.search(prefix[-20:] + " " + suffix[:20]))
        is_open = bool(plus or OPEN_PREFIX_RE.search(prefix) or OPEN_SUFFIX_RE.search(suffix))
        is_max = bool(MAX_PREFIX_RE.search(prefix) or MAX_SUFFIX_RE.search(suffix))

        if is_max and is_open:
            kind = "invalid"
            reason = "conflicting maximum and minimum wording"
        elif is_max and high is not None:
            kind = "invalid"
            reason = "maximum bound on a range"
        elif is_max:
            kind = "max"
            reason = "maximum bound"
            high = low
            low = 0.0
        elif is_open and high is not None:
            kind = "invalid"
            reason = "open-ended range"
        elif is_open:
            kind = "open"
            reason = "open-ended minimum"
        elif high is not None:
            if low > high:
                kind = "invalid"
                reason = "reversed range"
            elif low == high:
                kind = "exact"
                reason = "exact requirement"
            else:
                kind = "range"
                reason = "range"
        else:
            kind = "exact"
            reason = "exact requirement"

        constraints.append(
            _constraint(
                kind,
                low=low,
                high=high,
                optional=optional,
                evidence=_evidence(text, match, extra={"match": match.group(0).strip()}),
                reason=reason,
            )
        )

    for match in FRESHER_RE.finditer(text):
        prefix = text[max(0, match.start() - 40):match.start()]
        suffix = text[match.end():match.end() + 40]
        optional = bool(OPTIONAL_RE.search(prefix + " " + suffix))
        constraints.append(
            _constraint(
                "fresher",
                low=0.0,
                high=0.0,
                optional=optional,
                evidence=_evidence(text, match),
            )
        )
    return constraints


def _constraint_verdict(item):
    kind = item["kind"]
    if kind in ("invalid", "adversarial"):
        return "REVIEW"
    if kind == "fresher":
        return "ELIGIBLE"
    if kind == "max":
        return "ELIGIBLE"
    if kind == "open":
        if item["low"] <= 0:
            return "ELIGIBLE"
        if item["low"] <= MAX_EXPERIENCE:
            return "REVIEW"
        return "INELIGIBLE"
    if kind == "range":
        if item["low"] > MAX_EXPERIENCE:
            return "INELIGIBLE"
        if item["high"] <= MAX_EXPERIENCE:
            return "ELIGIBLE"
        return "REVIEW"
    if kind == "exact":
        return "ELIGIBLE" if item["low"] <= MAX_EXPERIENCE else "INELIGIBLE"
    return "REVIEW"


def _combine(verdicts):
    unique = set(verdicts)
    if not unique:
        return None
    if len(unique) == 1:
        return next(iter(unique))
    return "REVIEW"


def _reason_for(constraints, verdict):
    if not constraints:
        return "No usable experience evidence was found."
    required = [c for c in constraints if not c["optional"]] or constraints
    first = required[0]
    kind = first["kind"]
    low = _clean_number(first.get("low"))
    high = _clean_number(first.get("high"))
    if kind == "fresher":
        return "The posting explicitly accepts freshers or no prior experience."
    if kind == "exact":
        return f"The posting requires {low} years of experience."
    if kind == "range":
        return f"The posting gives a {low}-{high} year range."
    if kind == "open":
        return f"The posting gives an open-ended {low}+ year minimum."
    if kind == "max":
        upper = high if high is not None else low
        return f"The posting caps experience at {upper} years."
    if kind == "invalid":
        return f"The experience requirement is malformed: {first.get('reason', 'unreadable')}."
    if verdict == "REVIEW":
        return "The experience requirement is ambiguous."
    return "The posting requires more than two years of experience."


def _reason_code(constraints, verdict, structured_conflict=False):
    if structured_conflict:
        return "review_conflict"
    if not constraints:
        return "review_missing"
    required = [c for c in constraints if not c["optional"]]
    if not required:
        return "review_optional_only"
    first = required[0]
    kind = first["kind"]
    if kind == "invalid":
        return "review_malformed"
    if kind == "fresher":
        return "eligible_fresher"
    if kind == "max":
        return "eligible_max_bound"
    if kind == "open":
        return "eligible_open_zero" if first["low"] <= 0 else (
            "review_open_ended" if verdict == "REVIEW" else "ineligible_open_minimum"
        )
    if kind == "range":
        if first["low"] > 2:
            return "ineligible_range_minimum"
        if first["high"] <= 2:
            return "eligible_range"
        return "review_ambiguous_range"
    if kind == "exact":
        if first["low"] <= 2:
            return "eligible_exact"
        return "ineligible_exact"
    return "review_unknown"


def _structured(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def evaluate(
    text="",
    *,
    structured_min=None,
    seniority=None,
    title=None,
    checked_at=None,
    preserve_path=None,
):
    raw_text = str(text or "")
    cleaned = normalize_text(raw_text)
    timestamp = _iso(checked_at)
    structured_value = _structured(structured_min)
    if structured_min is not None and structured_value is None:
        return _result(
            "REVIEW",
            "review_malformed_structured",
            "The structured experience minimum is not a non-negative number.",
            [],
            None,
            seniority,
            raw_text,
            timestamp,
        )

    adversarial = ADVERSARIAL_RE.search(cleaned)
    if adversarial:
        return _result(
            "REVIEW",
            "review_adversarial",
            "The posting contains instruction-like or hidden-content signals; an LLM must not interpret it.",
            [_evidence(cleaned, adversarial, source="description")],
            structured_value,
            seniority,
            raw_text,
            timestamp,
            has_description=bool(cleaned),
        )

    constraints = _parse_constraints(cleaned)
    required = [c for c in constraints if not c["optional"]]
    evidence = []
    if structured_value is not None:
        evidence.append(
            {
                "source": "freehire",
                "field": "enrichment.experience_years_min",
                "value": _clean_number(structured_value),
                "text": f"enrichment.experience_years_min={_clean_number(structured_value)}",
            }
        )
    evidence.extend(c["evidence"] for c in constraints if c.get("evidence"))
    evidence = evidence[:12]

    if structured_value is not None and not required:
        verdict = "ELIGIBLE" if structured_value <= MAX_EXPERIENCE else "INELIGIBLE"
        code = "eligible_structured" if verdict == "ELIGIBLE" else "ineligible_structured"
        reason = (
            f"FreeHire reports a { _clean_number(structured_value) } year minimum."
            if verdict == "ELIGIBLE"
            else f"FreeHire reports a { _clean_number(structured_value) } year minimum, above the two-year limit."
        )
        return _result(
            verdict,
            code,
            reason,
            evidence,
            structured_value,
            seniority,
            raw_text,
            timestamp,
            preserve_path=preserve_path,
        )

    if structured_value is None and not required:
        if constraints:
            code, reason = "review_optional_only", "Only optional experience wording was found."
        elif seniority or title:
            code, reason = "review_seniority_only", "Only a seniority label was found; it is not an experience minimum."
        else:
            code, reason = "review_missing", "No usable experience minimum was found."
        if seniority and SENIORITY_SENIOR_RE.search(str(seniority)):
            code, reason = "review_seniority_only", f"Seniority '{seniority}' is not a numeric experience minimum."
        elif title and SENIOR_RE.search(str(title)):
            code, reason = "review_seniority_only", f"Title '{title}' is not a numeric experience minimum."
        return _result(
            "REVIEW",
            code,
            reason,
            evidence,
            None,
            seniority,
            raw_text,
            timestamp,
            preserve_path=preserve_path,
        )

    description_verdict = _combine([_constraint_verdict(c) for c in required]) if required else None
    description_code = _reason_code(required, description_verdict or "REVIEW")

    if structured_value is None:
        verdict = description_verdict or "REVIEW"
        code = description_code
        reason = _reason_for(required, verdict)
    else:
        structured_verdict = "ELIGIBLE" if structured_value <= MAX_EXPERIENCE else "INELIGIBLE"
        if description_verdict is None:
            verdict, code = structured_verdict, (
                "eligible_structured" if structured_verdict == "ELIGIBLE" else "ineligible_structured"
            )
            reason = (
                f"FreeHire reports a {_clean_number(structured_value)} year minimum."
                if verdict == "ELIGIBLE"
                else f"FreeHire reports a {_clean_number(structured_value)} year minimum, above the two-year limit."
            )
        elif description_verdict == structured_verdict:
            verdict = structured_verdict
            code = description_code if description_verdict == "ELIGIBLE" else (
                "eligible_structured" if structured_verdict == "ELIGIBLE" else "ineligible_structured"
            )
            reason = (
                _reason_for(required, verdict)
                if required
                else f"FreeHire reports a {_clean_number(structured_value)} year minimum."
            )
        else:
            verdict = "REVIEW"
            code = "review_conflict"
            reason = (
                f"Structured minimum {_clean_number(structured_value)} conflicts with the description's "
                f"{description_verdict.lower()} requirement."
            )

    if verdict == "ELIGIBLE" and (SENIORITY_SENIOR_RE.search(str(seniority or "")) or SENIOR_RE.search(str(title or ""))):
        verdict = "REVIEW"
        code = "review_seniority_conflict"
        reason = "A senior title or label conflicts with an otherwise eligible experience requirement."
    if adversarial:
        verdict = "REVIEW"
        code = "review_adversarial"
        reason = "Instruction-like content must be reviewed manually."

    minimum = structured_value
    maximum = None
    if required:
        maxima = [c["high"] for c in required if c.get("high") is not None]
        maximum = max(maxima) if maxima else None
        if minimum is None:
            minimum = min(c["low"] for c in required if c.get("low") is not None) if any(
                c.get("low") is not None for c in required
            ) else None
    return _result(
        verdict,
        code,
        reason,
        evidence,
        structured_value,
        seniority,
        raw_text,
        timestamp,
        minimum=minimum,
        maximum=maximum,
        has_description=bool(required),
        preserve_path=preserve_path,
    )


def _result(
    verdict,
    code,
    reason,
    evidence,
    structured_value,
    seniority,
    raw_text,
    timestamp,
    *,
    minimum=None,
    maximum=None,
    has_description=False,
    preserve_path=None,
):
    if preserve_path is not None:
        path = Path(preserve_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw_text.encode("utf-8"))
    return {
        "verdict": verdict,
        "allowed_for_apply": verdict == "ELIGIBLE",
        "reason_code": code,
        "reason": reason,
        "minimum_years": _clean_number(structured_value if minimum is None else minimum),
        "maximum_years": _clean_number(maximum),
        "structured_experience_years_min": _clean_number(structured_value),
        "seniority": str(seniority).strip() if seniority else None,
        "source": (
            "structured+description"
            if structured_value is not None and has_description
            else "structured"
            if structured_value is not None
            else "description"
            if evidence
            else "none"
        ),
        "evidence": evidence,
        "posting_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "posting_chars": len(raw_text),
        "checked_at": timestamp,
        "parser_version": PARSER_VERSION,
    }


def review_gate(code="review_missing", reason="No deterministic experience gate result was supplied.", checked_at=None):
    return {
        "verdict": "REVIEW",
        "allowed_for_apply": False,
        "reason_code": code,
        "reason": reason,
        "minimum_years": None,
        "maximum_years": None,
        "structured_experience_years_min": None,
        "seniority": None,
        "source": "none",
        "evidence": [],
        "posting_sha256": None,
        "posting_chars": 0,
        "checked_at": _iso(checked_at),
        "parser_version": PARSER_VERSION,
    }


def normalize_gate(value, checked_at=None):
    if not isinstance(value, dict):
        return review_gate("review_missing_gate", "The scoring result had no experience gate object.", checked_at)
    verdict = str(value.get("verdict", "")).strip().upper()
    if verdict not in VERDICTS:
        return review_gate("review_invalid_gate", "The experience gate verdict was not ELIGIBLE, INELIGIBLE, or REVIEW.", checked_at)
    code = str(value.get("reason_code") or "review_unspecified").strip()[:80]
    reason = str(value.get("reason") or "No reason supplied.").strip()[:500]
    evidence = []
    raw_evidence = value.get("evidence")
    if isinstance(raw_evidence, list):
        for item in raw_evidence[:12]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            clean = {
                "source": str(item.get("source") or "unknown")[:32],
                "text": text[:300],
            }
            if isinstance(item.get("start"), int) and item["start"] >= 0:
                clean["start"] = item["start"]
            if isinstance(item.get("end"), int) and item["end"] >= clean.get("start", 0):
                clean["end"] = item["end"]
            if "field" in item:
                clean["field"] = str(item["field"])[:80]
            if "match" in item:
                clean["match"] = str(item["match"])[:300]
            if "value" in item and isinstance(item["value"], (int, float)) and not isinstance(item["value"], bool):
                clean["value"] = item["value"]
            evidence.append(clean)
    source = str(value.get("source") or "none")
    if source not in SOURCES:
        source = "none"
    if verdict == "ELIGIBLE" and not evidence:
        return review_gate("review_missing_evidence", "An eligible gate must include posting evidence.", checked_at)
    try:
        checked = _iso(value.get("checked_at") or checked_at)
    except GateError:
        checked = _iso(checked_at)
    result = {
        "verdict": verdict,
        "allowed_for_apply": verdict == "ELIGIBLE",
        "reason_code": code,
        "reason": reason,
        "minimum_years": _safe_number(value.get("minimum_years")),
        "maximum_years": _safe_number(value.get("maximum_years")),
        "structured_experience_years_min": _safe_number(value.get("structured_experience_years_min")),
        "seniority": str(value["seniority"])[:80] if value.get("seniority") else None,
        "source": source,
        "evidence": evidence,
        "posting_sha256": (
            str(value["posting_sha256"])
            if isinstance(value.get("posting_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", value["posting_sha256"])
            else None
        ),
        "posting_chars": (
            int(value["posting_chars"])
            if isinstance(value.get("posting_chars"), int)
            and not isinstance(value.get("posting_chars"), bool)
            and value["posting_chars"] >= 0
            else 0
        ),
        "checked_at": checked,
        "parser_version": str(value.get("parser_version") or PARSER_VERSION)[:32],
    }
    return result


def _safe_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)) or value < 0:
        return None
    return _clean_number(float(value))


def _load_state(path):
    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GateError(f"cannot read state: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GateError(f"state is not valid JSON: {exc}") from exc
    seen = document.get("seen") if isinstance(document, dict) else None
    if not isinstance(seen, dict):
        raise GateError("state has no seen object")
    return document, seen


def _save_state(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _find_entry(seen, key=None, url=None):
    if key:
        entry = seen.get(key)
        if not isinstance(entry, dict):
            return None, None
        return key, entry
    if url:
        wanted = str(url).strip().rstrip("/")
        matches = [
            (candidate_key, entry)
            for candidate_key, entry in seen.items()
            if isinstance(entry, dict) and str(entry.get("url") or "").strip().rstrip("/") == wanted
        ]
        if len(matches) == 1:
            return matches[0]
        return None, None
    raise GateError("provide --key or --url")


def override_allows(gate, override):
    if not isinstance(gate, dict) or gate.get("verdict") == "ELIGIBLE":
        return bool(isinstance(gate, dict) and gate.get("verdict") == "ELIGIBLE")
    if not isinstance(override, dict):
        return False
    reason = str(override.get("reason") or "").strip()
    at = str(override.get("at") or "").strip()
    checked = str(gate.get("checked_at") or "").strip()
    if not reason or not at or not checked:
        return False
    try:
        override_time = datetime.fromisoformat(at.replace("Z", "+00:00"))
        gate_time = datetime.fromisoformat(checked.replace("Z", "+00:00"))
    except ValueError:
        return False
    return override_time >= gate_time


def _force_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _print(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _read_text(args):
    if args.text is not None and args.infile is not None:
        raise GateError("use only one of --text and --in")
    if args.text is not None:
        return args.text
    if args.infile is not None:
        try:
            return Path(args.infile).read_text(encoding="utf-8")
        except OSError as exc:
            raise GateError(f"cannot read input: {exc}") from exc
    return sys.stdin.read()


def _add_now(parser):
    parser.add_argument("--now", default=None, help="fixed UTC timestamp for checked_at/override")


def _build_parser():
    parser = argparse.ArgumentParser(prog="experience_gate.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="evaluate posting text")
    evaluate_parser.add_argument("--in", dest="infile", type=Path, default=None)
    evaluate_parser.add_argument("--text", default=None)
    evaluate_parser.add_argument("--structured-min", type=float, default=None)
    evaluate_parser.add_argument("--seniority", default=None)
    evaluate_parser.add_argument("--title", default=None)
    evaluate_parser.add_argument("--preserve", type=Path, default=None)
    _add_now(evaluate_parser)

    check_parser = sub.add_parser("check", help="check stored gate for /apply")
    check_parser.add_argument("--key", default=None)
    check_parser.add_argument("--url", default=None)
    check_parser.add_argument("--state", type=Path, default=STATE)
    _add_now(check_parser)

    record_parser = sub.add_parser("record", help="evaluate and store a gate")
    record_parser.add_argument("--key", required=True)
    record_parser.add_argument("--in", dest="infile", type=Path, default=None)
    record_parser.add_argument("--text", default=None)
    record_parser.add_argument("--structured-min", type=float, default=None)
    record_parser.add_argument("--seniority", default=None)
    record_parser.add_argument("--title", default=None)
    record_parser.add_argument("--state", type=Path, default=STATE)
    _add_now(record_parser)

    override_parser = sub.add_parser("override", help="record an explicit manual override")
    override_parser.add_argument("--key", default=None)
    override_parser.add_argument("--url", default=None)
    override_parser.add_argument("--reason", required=True)
    override_parser.add_argument("--confirm", action="store_true")
    override_parser.add_argument("--state", type=Path, default=STATE)
    _add_now(override_parser)
    return parser


def main(argv=None):
    _force_utf8_output()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            text = _read_text(args)
            _print(
                evaluate(
                    text,
                    structured_min=args.structured_min,
                    seniority=args.seniority,
                    title=args.title,
                    checked_at=args.now,
                    preserve_path=args.preserve,
                )
            )
            return 0

        document, seen = _load_state(args.state)

        if args.command == "check":
            key, entry = _find_entry(seen, args.key, args.url)
            if key is None:
                gate = review_gate("review_not_found", "No stored job matched this key or URL.", args.now)
                _print({"found": False, "key": args.key, "verdict": "REVIEW", "experience_gate": gate, "override": None, "override_valid": False, "allowed_for_apply": False})
                return 0
            gate = normalize_gate(entry.get("experience_gate"), args.now)
            override = entry.get("experience_override") if isinstance(entry.get("experience_override"), dict) else None
            valid = override_allows(gate, override)
            _print(
                {
                    "found": True,
                    "key": key,
                    "title": entry.get("title"),
                    "company": entry.get("company"),
                    "url": entry.get("url"),
                    "experience_gate": gate,
                    "override": override,
                    "override_valid": valid,
                    "allowed_for_apply": gate["verdict"] == "ELIGIBLE" or valid,
                }
            )
            return 0

        if args.command == "record":
            if args.key not in seen or not isinstance(seen[args.key], dict):
                raise GateError(f"unknown key: {args.key}")
            gate = evaluate(
                _read_text(args),
                structured_min=args.structured_min,
                seniority=args.seniority,
                title=args.title,
                checked_at=args.now,
            )
            seen[args.key]["experience_gate"] = gate
            _save_state(args.state, document)
            _print({"key": args.key, "experience_gate": gate})
            return 0

        if args.command == "override":
            if not args.confirm:
                raise GateError("--confirm is required for a manual override")
            reason = str(args.reason or "").strip()
            if len(reason) < 10:
                raise GateError("override reason must be at least 10 characters")
            key, entry = _find_entry(seen, args.key, args.url)
            if key is None:
                raise GateError("no stored job matched this key or URL")
            gate = normalize_gate(entry.get("experience_gate"), args.now)
            if gate["verdict"] == "ELIGIBLE":
                raise GateError("the stored experience gate is already ELIGIBLE")
            entry["experience_override"] = {
                "reason": reason[:500],
                "at": _iso(args.now),
                "gate_checked_at": gate.get("checked_at"),
                "previous_verdict": gate.get("verdict"),
                "previous_reason_code": gate.get("reason_code"),
            }
            _save_state(args.state, document)
            _print({"key": key, "override": entry["experience_override"], "experience_gate": gate, "allowed_for_apply": True})
            return 0
    except GateError as exc:
        print(f"experience_gate: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
