"""Raw record → `Candidate` parser.

The hackathon's exact field names are not pinned (different bundles have
shipped slightly different key conventions). The parser is therefore
defensive: it accepts a handful of common aliases per field, falls back
gracefully when fields are missing, and keeps the raw dict on
`Candidate.raw` so downstream code can recover anything we did not map.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from app.core.logging import get_logger
from app.intelligence.domain import (
    BehavioralSignals,
    Candidate,
    CandidateProfile,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    Skill,
)
from app.intelligence.preprocessors.dates import (
    duration_years,
    parse_date_value,
    parse_year,
)

logger = get_logger(__name__)

_NUMERIC_GRADE_RE = re.compile(r"[-+]?\d*\.?\d+")


def _pick(record: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first non-empty value among `keys`.

    Empty strings, empty lists, and `None` are treated as missing so a
    record that has both ``"current_title": ""`` and ``"title": "Engineer"``
    resolves to the meaningful value.
    """
    for key in keys:
        if key in record:
            value = record[key]
            if value not in (None, "", [], {}):
                return value
    return default


def _pick_multi(
    *sources: Mapping[str, Any] | None,
    keys: tuple[str, ...],
    default: Any = None,
) -> Any:
    """`_pick` across multiple source dicts in order.

    Useful when a field may live at the record root *or* nested under a
    `profile` block (as the Redrob schema does).
    """
    for source in sources:
        if not source:
            continue
        value = _pick(source, *keys)
        if value not in (None, "", [], {}):
            return value
    return default


def _as_list(value: Any) -> list[Any]:
    """Coerce a value to a list, treating None as empty."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_float(value: Any) -> float | None:
    """Best-effort float coercion that returns `None` instead of raising."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    """Best-effort int coercion."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    """Coerce a value to bool, treating string forms like 'yes' as truthy."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False
    return None


def _extract_numeric_grade(value: Any) -> float | None:
    """Pull a numeric grade out of a free-form string.

    Examples:
        ``"8.24 CGPA"``    -> 8.24
        ``"3.85 GPA"``     -> 3.85
        ``"First Class"``  -> None
        ``88.5``           -> 88.5
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = _NUMERIC_GRADE_RE.search(value)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


class CandidateParser:
    """Deterministically converts a raw record into a `Candidate`."""

    def parse(self, record: Mapping[str, Any]) -> Candidate:
        """Convert a raw record dictionary to a `Candidate`.

        Args:
            record: Raw dictionary loaded from the JSONL stream.

        Returns:
            A populated `Candidate`.

        Raises:
            ValueError: When the record has no usable candidate id.
        """
        candidate_id = _pick(record, "candidate_id", "id", "candidateId")
        if not candidate_id:
            raise ValueError("Record is missing a candidate_id")

        profile = self._parse_profile(record, candidate_id)
        experience = self._parse_experience(record)
        education = self._parse_education(record)
        skills = self._parse_skills(record)
        certifications = self._parse_certifications(record)
        languages = self._parse_languages(record)
        signals = self._parse_signals(record)

        # Backfill total experience if missing but we can sum tenures.
        if profile.total_experience_years is None and experience:
            tenures = [e.duration_years for e in experience if e.duration_years]
            if tenures:
                profile.total_experience_years = round(sum(tenures), 2)

        return Candidate(
            candidate_id=str(candidate_id),
            profile=profile,
            experience=experience,
            education=education,
            skills=skills,
            certifications=certifications,
            languages=languages,
            signals=signals,
            raw=dict(record),
        )

    # ------------------------------------------------------------------
    # Section parsers
    # ------------------------------------------------------------------
    def _parse_profile(
        self, record: Mapping[str, Any], candidate_id: str
    ) -> CandidateProfile:
        nested = record.get("profile") if isinstance(record.get("profile"), Mapping) else None

        return CandidateProfile(
            candidate_id=str(candidate_id),
            name=_pick_multi(
                nested, record, keys=("anonymized_name", "name", "full_name", "candidate_name")
            ),
            headline=_pick_multi(nested, record, keys=("headline", "tagline")),
            current_title=_pick_multi(
                nested,
                record,
                keys=("current_title", "title", "current_role", "designation"),
            ),
            current_company=_pick_multi(
                nested, record, keys=("current_company", "company", "employer")
            ),
            current_company_size=_pick_multi(
                nested, record, keys=("current_company_size", "company_size")
            ),
            current_industry=_pick_multi(
                nested, record, keys=("current_industry", "industry")
            ),
            location=_pick_multi(
                nested, record, keys=("location", "city", "current_location")
            ),
            country=_pick_multi(nested, record, keys=("country",)),
            total_experience_years=_coerce_float(
                _pick_multi(
                    nested,
                    record,
                    keys=(
                        "years_of_experience",
                        "total_experience_years",
                        "experience_years",
                        "total_experience",
                    ),
                )
            ),
            summary=_pick_multi(nested, record, keys=("summary", "about", "bio")),
            email=_pick_multi(nested, record, keys=("email", "contact_email")),
        )

    def _parse_experience(self, record: Mapping[str, Any]) -> list[ExperienceEntry]:
        entries = _as_list(
            _pick(
                record,
                "career_history",
                "experience",
                "work_experience",
                "employment_history",
                "jobs",
            )
        )
        parsed: list[ExperienceEntry] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            start = parse_date_value(_pick(entry, "start_date", "from", "start"))
            end_raw = _pick(entry, "end_date", "to", "end")
            is_current_flag = _coerce_bool(_pick(entry, "is_current", "current"))
            is_current = (
                bool(is_current_flag)
                if is_current_flag is not None
                else end_raw in (None, "", "present", "Present", "current")
            )
            end = None if is_current else parse_date_value(end_raw)

            duration_months = _coerce_int(
                _pick(entry, "duration_months", "duration_in_months")
            )
            if duration_months is not None and duration_months >= 0:
                duration_yrs = round(duration_months / 12.0, 2)
            else:
                duration_yrs = duration_years(start, end)

            parsed.append(
                ExperienceEntry(
                    company=_pick(entry, "company", "employer", "organization"),
                    title=_pick(entry, "title", "role", "designation"),
                    start_date=start,
                    end_date=end,
                    is_current=is_current,
                    description=_pick(entry, "description", "summary"),
                    location=_pick(entry, "location", "city"),
                    duration_years=duration_yrs,
                    duration_months=duration_months,
                    industry=_pick(entry, "industry"),
                    company_size=_pick(entry, "company_size"),
                )
            )
        return parsed

    def _parse_education(self, record: Mapping[str, Any]) -> list[EducationEntry]:
        entries = _as_list(_pick(record, "education", "academics"))
        parsed: list[EducationEntry] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            grade_raw = _pick(entry, "grade", "gpa", "cgpa", "score")
            grade_text = (
                str(grade_raw).strip() if isinstance(grade_raw, str) else None
            )
            parsed.append(
                EducationEntry(
                    institution=_pick(
                        entry, "institution", "school", "university", "college"
                    ),
                    degree=_pick(entry, "degree", "qualification"),
                    field_of_study=_pick(entry, "field_of_study", "field", "major"),
                    start_year=parse_year(_pick(entry, "start_year", "from")),
                    end_year=parse_year(
                        _pick(entry, "end_year", "graduation_year", "to")
                    ),
                    grade=grade_text,
                    gpa=_extract_numeric_grade(grade_raw),
                    tier=_pick(entry, "tier", "institution_tier"),
                )
            )
        return parsed

    def _parse_skills(self, record: Mapping[str, Any]) -> list[Skill]:
        entries = _as_list(_pick(record, "skills"))
        parsed: list[Skill] = []
        for entry in entries:
            if isinstance(entry, str):
                parsed.append(Skill(name=entry))
                continue
            if isinstance(entry, Mapping):
                name = _pick(entry, "name", "skill", "title")
                if not name:
                    continue
                duration_months = _coerce_int(
                    _pick(entry, "duration_months", "duration_in_months")
                )
                years_used = _coerce_float(_pick(entry, "years_used", "years", "yoe"))
                if years_used is None and duration_months is not None:
                    years_used = round(duration_months / 12.0, 2)
                parsed.append(
                    Skill(
                        name=str(name),
                        proficiency=_pick(entry, "proficiency", "level", "score"),
                        years_used=years_used,
                        last_used_year=parse_year(
                            _pick(entry, "last_used_year", "last_used")
                        ),
                        duration_months=duration_months,
                        endorsements=_coerce_int(
                            _pick(entry, "endorsements", "endorsement_count")
                        ),
                    )
                )
        return parsed

    def _parse_languages(self, record: Mapping[str, Any]) -> list[LanguageEntry]:
        entries = _as_list(_pick(record, "languages"))
        parsed: list[LanguageEntry] = []
        for entry in entries:
            if isinstance(entry, str):
                parsed.append(LanguageEntry(name=entry))
                continue
            if isinstance(entry, Mapping):
                name = _pick(entry, "language", "name")
                if not name:
                    continue
                parsed.append(
                    LanguageEntry(
                        name=str(name),
                        proficiency=_pick(entry, "proficiency", "level"),
                    )
                )
        return parsed

    def _parse_certifications(
        self, record: Mapping[str, Any]
    ) -> list[CertificationEntry]:
        entries = _as_list(_pick(record, "certifications", "certificates"))
        parsed: list[CertificationEntry] = []
        for entry in entries:
            if isinstance(entry, str):
                parsed.append(CertificationEntry(name=entry))
                continue
            if isinstance(entry, Mapping):
                name = _pick(entry, "name", "title", "certificate")
                if not name:
                    continue
                parsed.append(
                    CertificationEntry(
                        name=str(name),
                        issuer=_pick(entry, "issuer", "authority", "provider"),
                        issued_year=parse_year(
                            _pick(entry, "year", "issued_year", "issued")
                        ),
                        expires_year=parse_year(
                            _pick(entry, "expires_year", "expires", "expiry")
                        ),
                    )
                )
        return parsed

    def _parse_signals(self, record: Mapping[str, Any]) -> BehavioralSignals:
        block = _pick(record, "redrob_signals", "signals", "behavioral_signals")
        if not isinstance(block, Mapping):
            return BehavioralSignals()

        salary_block = block.get("expected_salary_range_inr_lpa") or {}
        if not isinstance(salary_block, Mapping):
            salary_block = {}

        assessments = block.get("skill_assessment_scores") or {}
        if not isinstance(assessments, Mapping):
            assessments = {}

        return BehavioralSignals(
            profile_completeness_score=_coerce_float(
                block.get("profile_completeness_score")
            ),
            signup_date=parse_date_value(block.get("signup_date")),
            last_active_date=parse_date_value(block.get("last_active_date")),
            open_to_work_flag=_coerce_bool(block.get("open_to_work_flag")),
            profile_views_received_30d=_coerce_int(
                block.get("profile_views_received_30d")
            ),
            applications_submitted_30d=_coerce_int(
                block.get("applications_submitted_30d")
            ),
            recruiter_response_rate=_coerce_float(
                block.get("recruiter_response_rate")
            ),
            avg_response_time_hours=_coerce_float(
                block.get("avg_response_time_hours")
            ),
            skill_assessment_scores={
                str(k): float(v)
                for k, v in assessments.items()
                if _coerce_float(v) is not None
            },
            connection_count=_coerce_int(block.get("connection_count")),
            endorsements_received=_coerce_int(block.get("endorsements_received")),
            notice_period_days=_coerce_int(block.get("notice_period_days")),
            expected_salary_min_lpa=_coerce_float(salary_block.get("min")),
            expected_salary_max_lpa=_coerce_float(salary_block.get("max")),
            preferred_work_mode=_pick_str(block, "preferred_work_mode"),
            willing_to_relocate=_coerce_bool(block.get("willing_to_relocate")),
            github_activity_score=_coerce_float(block.get("github_activity_score")),
            search_appearance_30d=_coerce_int(block.get("search_appearance_30d")),
            saved_by_recruiters_30d=_coerce_int(
                block.get("saved_by_recruiters_30d")
            ),
            interview_completion_rate=_coerce_float(
                block.get("interview_completion_rate")
            ),
            offer_acceptance_rate=_coerce_float(block.get("offer_acceptance_rate")),
            verified_email=_coerce_bool(block.get("verified_email")),
            verified_phone=_coerce_bool(block.get("verified_phone")),
            linkedin_connected=_coerce_bool(block.get("linkedin_connected")),
        )


def _pick_str(record: Mapping[str, Any], *keys: str) -> str | None:
    """Variant of `_pick` that always returns either a non-empty str or None."""
    value = _pick(record, *keys)
    if value is None:
        return None
    return str(value).strip() or None


def parse_many(records: Iterable[Mapping[str, Any]]) -> list[Candidate]:
    """Convenience helper to parse a small in-memory batch (tests, REPL).

    For the 100k-candidate pool, prefer `CandidateLoader.iter_candidates`
    which streams one record at a time.

    Args:
        records: Iterable of raw record dicts.

    Returns:
        List of parsed `Candidate` objects.
    """
    parser = CandidateParser()
    parsed: list[Candidate] = []
    for record in records:
        try:
            parsed.append(parser.parse(record))
        except Exception:  # noqa: BLE001
            logger.exception("parser.failed", candidate_id=record.get("candidate_id"))
    return parsed
