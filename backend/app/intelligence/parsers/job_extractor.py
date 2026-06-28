"""Structured extraction of intelligence from a job description.

Phase 3 builds on the heuristic :class:`JDParser` (Phase 2) and adds
a taxonomy-driven NLP layer that:

* Detects mentions of well-known skills, frameworks, languages, tools,
  databases, clouds, and domain concepts using the curated taxonomy and
  the alias map.
* Buckets the matches into structured categories (programming languages,
  tools/frameworks, domain knowledge, soft skills, ...).
* Extracts experience ranges, an experience level label, role title,
  responsibilities (verb-led bullets), and qualifications (education /
  degree bullets).
* Hands back a single :class:`JobExtraction` record that the persistence
  and matching layers consume.

The extractor never modifies Phase-1/2 code paths; it composes them.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Final

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.intelligence.domain import JobProfile
from app.intelligence.parsers.jd_parser import JDParser
from app.intelligence.skills.normalizer import SkillNormalizer
from app.intelligence.skills.taxonomy import (
    SKILL_TAXONOMY,
    SOFT_SKILL_KEYWORDS,
    SkillCategory,
)

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Output record
# ----------------------------------------------------------------------
class JobExtraction(BaseModel):
    """Structured intelligence pulled from a job description.

    All ``list`` fields are deduplicated and order-stable so the
    persisted payload is reproducible.
    """

    title: str | None = None
    role: str | None = None
    industry: str | None = None

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    tools_frameworks: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)

    extracted_keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)

    experience_min_years: float | None = None
    experience_max_years: float | None = None
    experience_level: str | None = None

    job_profile: JobProfile | None = Field(default=None, exclude=True)
    """Phase-2 :class:`JobProfile` produced by the underlying heuristic
    parser. Carried alongside the extraction for downstream Phase-4
    components that already speak that shape."""


# ----------------------------------------------------------------------
# Heuristic resources
# ----------------------------------------------------------------------
_VERB_HEAD_RE = re.compile(
    r"^\s*(build|design|develop|maintain|own|lead|drive|architect|ship|"
    r"deliver|optimi[sz]e|deploy|implement|create|collaborate|mentor|"
    r"prototype|operate|monitor|train|fine[- ]?tune|evaluate|research|"
    r"scale|integrate|partner|coordinate|review|measure|improve)",
    re.IGNORECASE,
)

_DEGREE_RE = re.compile(
    r"\b(b\.?(?:sc|tech|e|s|a)|m\.?(?:sc|tech|s|e|a|ba)|"
    r"ph\.?d|doctorate|bachelor|master|graduate|undergraduate|"
    r"degree)\b",
    re.IGNORECASE,
)

_EDUCATION_LINE_RE = re.compile(
    r"\b(bachelor|master|ph\.?d|doctorate|degree|"
    r"b\.?(?:sc|tech|e|s|a)|m\.?(?:sc|tech|s|e|a|ba))\b",
    re.IGNORECASE,
)

_QUALIFICATION_HEADINGS: Final[tuple[str, ...]] = (
    "qualifications",
    "minimum qualifications",
    "education",
    "what you bring",
    "requirements",
    "things you absolutely need",
    "must have",
    "must-have",
)

_RESPONSIBILITY_HEADINGS: Final[tuple[str, ...]] = (
    "responsibilities",
    "what you'll do",
    "what you will do",
    "your role",
    "day to day",
    "day-to-day",
    "the role",
    "key responsibilities",
)

_PROGRAMMING_LANGUAGE_FALLBACKS: Final[tuple[str, ...]] = (
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C",
    "Go", "Rust", "Ruby", "PHP", "Scala", "Kotlin", "Swift", "R",
    "SQL", "Bash", "Perl",
)

_EXP_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:[-–to]+|\s+to\s+)\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_EXP_MIN_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", re.IGNORECASE
)


# ----------------------------------------------------------------------
# Extractor
# ----------------------------------------------------------------------
class JobExtractor:
    """NLP-lite job-description extractor.

    The implementation is intentionally regex + taxonomy driven (no heavy
    runtime ML dependencies). This keeps Phase 3 deterministic, easy to
    test, and trivially deployable on CPU-only hosts. The taxonomy can
    be extended by passing ``extra_aliases`` to the normalizer or
    monkey-patching :data:`SKILL_TAXONOMY` at import time.
    """

    def __init__(
        self,
        *,
        normalizer: SkillNormalizer | None = None,
        jd_parser: JDParser | None = None,
    ) -> None:
        """Build an extractor.

        Args:
            normalizer: Pre-configured :class:`SkillNormalizer`. Defaults
                to a normalizer with fuzzy matching enabled.
            jd_parser: Pre-configured :class:`JDParser`. Defaults to one
                with stock headings.
        """
        self.normalizer = normalizer or SkillNormalizer()
        self.jd_parser = jd_parser or JDParser()

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------
    def extract(self, text: str, *, title: str | None = None) -> JobExtraction:
        """Run full structured extraction over a raw JD blob.

        Args:
            text: The full JD text. Markdown structure is preferred but
                plain text also works.
            title: Optional caller-supplied job title that overrides the
                heuristic role-title detection.

        Returns:
            A populated :class:`JobExtraction` record.
        """
        if not text or not text.strip():
            logger.warning("job_extractor.empty_input")
            return JobExtraction(title=title)

        profile = self.jd_parser.parse(text)
        resolved_title = title or profile.role_title

        required_raw = list(profile.required_skills)
        preferred_raw = list(profile.preferred_skills)

        # When the JD is unstructured (no required/preferred bullets at
        # all), fall back to a full-text taxonomy sweep so we still
        # produce a useful skill list. Structured JDs are taken at face
        # value to avoid bleeding skills between buckets.
        unstructured = not required_raw and not preferred_raw

        # 1. Required / preferred skill canonicalization.
        required = self._canonicalize_skill_lines(
            required_raw, text, sweep_full_text=unstructured
        )
        preferred = self._canonicalize_skill_lines(
            preferred_raw, text, exclude=required, sweep_full_text=False
        )

        # 2. Bucket the canonicalized skills by taxonomy category.
        combined = required + [s for s in preferred if s not in required]
        languages = self._filter_category(
            combined, SkillCategory.PROGRAMMING_LANGUAGE
        )
        tools_frameworks = self._filter_categories(
            combined,
            {
                SkillCategory.FRAMEWORK,
                SkillCategory.LIBRARY,
                SkillCategory.TOOL,
                SkillCategory.DATABASE,
                SkillCategory.CLOUD,
            },
        )
        domain_knowledge = self._filter_category(combined, SkillCategory.DOMAIN)

        # Fallback language detection for JDs that don't bullet-list them.
        if not languages:
            languages = self._detect_languages_from_text(text)
            for lang in languages:
                if lang not in required and lang not in preferred:
                    required.append(lang)

        # 3. Soft skills.
        soft_skills = self._extract_soft_skills(text)

        # 4. Responsibilities & qualifications by heading + heuristics.
        responsibilities = self._extract_responsibilities(text, profile)
        qualifications = self._extract_qualifications(text, profile)
        education = self._extract_education(qualifications, text)

        # 5. Disqualifiers come straight from the JD parser.
        disqualifiers = profile.disqualifiers

        # 6. Keyword bag: union of all surfaced concepts, lower-cased,
        #    so downstream BM25 / hashing layers have a single source.
        keywords = self._build_keyword_bag(
            required, preferred, soft_skills, languages,
            tools_frameworks, domain_knowledge, profile.required_keywords,
        )

        # 7. Experience level + range.
        exp_min, exp_max = (
            profile.experience_min_years,
            profile.experience_max_years,
        )
        if exp_min is None and exp_max is None:
            exp_min, exp_max = self._extract_experience(text)
        level = self._classify_experience_level(exp_min, exp_max, text)

        return JobExtraction(
            title=resolved_title,
            role=resolved_title,
            industry=profile.industry,
            required_skills=required,
            preferred_skills=preferred,
            soft_skills=soft_skills,
            tools_frameworks=tools_frameworks,
            programming_languages=languages,
            domain_knowledge=domain_knowledge,
            responsibilities=responsibilities,
            qualifications=qualifications,
            education_requirements=education,
            disqualifiers=disqualifiers,
            extracted_keywords=keywords,
            locations=list(profile.locations),
            experience_min_years=exp_min,
            experience_max_years=exp_max,
            experience_level=level,
            job_profile=profile,
        )

    # ------------------------------------------------------------------
    # Skill helpers
    # ------------------------------------------------------------------
    def _canonicalize_skill_lines(
        self,
        lines: list[str],
        full_text: str,
        *,
        exclude: Iterable[str] | None = None,
        sweep_full_text: bool = False,
    ) -> list[str]:
        """Turn free-text bullets into a list of canonical skill names.

        The strategy is: scan each bullet for taxonomy hits (more
        reliable than treating the whole bullet as a skill name).
        When nothing matches, normalize the bullet itself so at least
        a presentation-friendly form survives.

        Args:
            lines: Bullet lines collected for this bucket.
            full_text: The full JD text, used only when
                ``sweep_full_text=True``.
            exclude: Canonical names that must not appear in the output.
            sweep_full_text: When True, also scan the whole JD for
                taxonomy hits. Only set this for unstructured JDs
                without explicit required/preferred bullets — otherwise
                it bleeds skills from one bucket into another.
        """
        excluded = {s.lower() for s in (exclude or [])}
        emitted: list[str] = []
        seen: set[str] = set()

        for line in lines:
            hits = self._taxonomy_hits(line)
            if not hits:
                fallback = self.normalizer.normalize(line)
                if fallback:
                    hits = [fallback]
            for canonical in hits:
                key = canonical.lower()
                if key in excluded or key in seen:
                    continue
                seen.add(key)
                emitted.append(canonical)

        if sweep_full_text:
            for canonical in self._taxonomy_hits(full_text):
                key = canonical.lower()
                if key in excluded or key in seen:
                    continue
                seen.add(key)
                emitted.append(canonical)

        return emitted

    def _taxonomy_hits(self, text: str) -> list[str]:
        """Return canonical skills detected in ``text`` via the taxonomy."""
        if not text:
            return []
        lowered = f" {text.lower()} "
        hits: list[str] = []
        seen: set[str] = set()

        def _add(canonical: str) -> None:
            key = canonical.lower()
            if key in seen:
                return
            seen.add(key)
            hits.append(canonical)

        # Direct canonical names.
        for canonical in SKILL_TAXONOMY:
            needle = canonical.lower()
            if self._contains_skill(lowered, needle):
                _add(canonical)

        # Aliases mapped to their canonical form.
        for alias, canonical in self.normalizer._alias_index.items():  # noqa: SLF001
            if alias and self._contains_skill(lowered, alias):
                _add(canonical)

        return hits

    @staticmethod
    def _contains_skill(haystack_lower: str, needle_lower: str) -> bool:
        """Whole-token substring check tolerant of skill punctuation.

        ``needle_lower`` is treated as a complete skill phrase. We
        require the surrounding characters to be non-word so that
        ``"go"`` does not match inside ``"google"`` but does match in
        ``"go,"`` or ``"go."``.
        """
        if not needle_lower:
            return False
        if needle_lower not in haystack_lower:
            return False

        # Build a tolerant regex: punctuation in the needle is matched
        # literally; word boundaries are enforced at the ends.
        pattern = re.escape(needle_lower)
        return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", haystack_lower) is not None

    @staticmethod
    def _filter_category(
        skills: list[str], category: SkillCategory
    ) -> list[str]:
        """Return skills that match exactly one taxonomy category."""
        return [s for s in skills if SKILL_TAXONOMY.get(s) == category]

    @staticmethod
    def _filter_categories(
        skills: list[str], categories: set[SkillCategory]
    ) -> list[str]:
        """Return skills that match any of the given taxonomy categories."""
        return [s for s in skills if SKILL_TAXONOMY.get(s) in categories]

    def _detect_languages_from_text(self, text: str) -> list[str]:
        """Fallback: scan raw text for well-known programming languages."""
        lowered = f" {text.lower()} "
        found: list[str] = []
        for lang in _PROGRAMMING_LANGUAGE_FALLBACKS:
            if self._contains_skill(lowered, lang.lower()):
                found.append(lang)
        return found

    # ------------------------------------------------------------------
    # Soft skills
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_soft_skills(text: str) -> list[str]:
        lowered = text.lower()
        found: list[str] = []
        for canonical, needles in SOFT_SKILL_KEYWORDS.items():
            if any(n in lowered for n in needles):
                found.append(canonical)
        return found

    # ------------------------------------------------------------------
    # Responsibilities / qualifications
    # ------------------------------------------------------------------
    def _extract_responsibilities(
        self, text: str, profile: JobProfile
    ) -> list[str]:
        bullets = self._bullets_under_headings(text, _RESPONSIBILITY_HEADINGS)
        if bullets:
            return bullets
        # Fallback: pick verb-led bullets from anywhere in the doc.
        verb_bullets: list[str] = []
        for match in re.finditer(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$", text, re.MULTILINE):
            bullet = match.group(1).strip()
            if _VERB_HEAD_RE.match(bullet) and bullet not in profile.required_skills:
                verb_bullets.append(bullet)
        return verb_bullets[:20]

    def _extract_qualifications(
        self, text: str, profile: JobProfile
    ) -> list[str]:
        bullets = self._bullets_under_headings(text, _QUALIFICATION_HEADINGS)
        if bullets:
            return bullets
        # Fall back to the required-skill bullets the JDParser already
        # collected — those are effectively the qualifications.
        return list(profile.required_skills)

    @staticmethod
    def _extract_education(
        qualifications: Iterable[str], text: str
    ) -> list[str]:
        """Lines that mention an academic degree."""
        candidates: list[str] = []
        for line in qualifications:
            if _EDUCATION_LINE_RE.search(line):
                candidates.append(line.strip())
        if candidates:
            return candidates

        # Scan body for stray degree lines.
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or len(line) > 240:
                continue
            if _DEGREE_RE.search(line):
                candidates.append(line)
            if len(candidates) >= 5:
                break
        return candidates

    @staticmethod
    def _bullets_under_headings(
        text: str, headings: tuple[str, ...]
    ) -> list[str]:
        sections = re.split(r"(?m)^#{1,6}\s+(.*)$", text)
        # Result is alternating: preamble, heading1, body1, heading2, body2, ...
        bullets: list[str] = []
        for i in range(1, len(sections), 2):
            heading = sections[i].strip().lower()
            body = sections[i + 1] if i + 1 < len(sections) else ""
            if not any(h in heading for h in headings):
                continue
            for match in re.finditer(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$", body, re.MULTILINE):
                bullet = match.group(1).strip()
                if bullet:
                    bullets.append(bullet)
        return bullets

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_experience(text: str) -> tuple[float | None, float | None]:
        range_match = _EXP_RANGE_RE.search(text)
        if range_match:
            return float(range_match.group(1)), float(range_match.group(2))
        min_match = _EXP_MIN_RE.search(text)
        if min_match:
            return float(min_match.group(1)), None
        return None, None

    @staticmethod
    def _classify_experience_level(
        exp_min: float | None,
        exp_max: float | None,
        text: str,
    ) -> str | None:
        """Map a years range + JD text to a coarse level label.

        Numeric range takes precedence: stray mentions of "junior" /
        "senior" in the body (e.g. "mentor junior engineers") should
        not override an explicit 2-4 year requirement. Text keywords
        are consulted only when the JD does not specify a range.
        """
        if exp_min is not None or exp_max is not None:
            floor = exp_min if exp_min is not None else (exp_max or 0.0)
            if floor >= 8:
                return "Principal"
            if floor >= 5:
                return "Senior"
            if floor >= 2:
                return "Mid"
            return "Junior"

        lowered = text.lower()
        for needle, label in (
            ("principal", "Principal"),
            ("staff engineer", "Staff"),
            ("senior", "Senior"),
            ("lead engineer", "Lead"),
            ("entry-level", "Junior"),
            ("entry level", "Junior"),
            ("junior", "Junior"),
            ("intern", "Intern"),
        ):
            if needle in lowered:
                return label
        return None

    # ------------------------------------------------------------------
    # Keyword bag
    # ------------------------------------------------------------------
    @staticmethod
    def _build_keyword_bag(*sources: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for src in sources:
            for value in src:
                if not value:
                    continue
                key = value.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append(key)
        return out


def extract_job_intelligence(
    text: str,
    *,
    title: str | None = None,
) -> JobExtraction:
    """Convenience wrapper that uses default extractor settings.

    Args:
        text: Raw JD text.
        title: Optional caller-supplied job title.

    Returns:
        A populated :class:`JobExtraction`.
    """
    return JobExtractor().extract(text, title=title)


__all__ = ["JobExtraction", "JobExtractor", "extract_job_intelligence"]
