"""Heuristic parser for plain-text / Markdown job descriptions.

The hackathon JD is Markdown with descriptive section headings (e.g.
"Things you absolutely need", "Things we explicitly do NOT want"). The
heuristic parser:

1. Splits the text into sections by Markdown heading.
2. Maps known section names to required / preferred / disqualifier
   buckets.
3. Extracts experience ranges, location lists, and a role title from
   structured prefix lines (``Location:``, ``Experience Required:``, etc.).

Whenever a curated `JobProfile` YAML is available, prefer
`load_job_profile_yaml` over this heuristic. The heuristic is here so the
pipeline can still produce a reasonable `JobProfile` from raw text.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.core.logging import get_logger
from app.intelligence.domain import JobProfile

logger = get_logger(__name__)


# Heading → bucket mapping. Lower-cased; partial-match on heading text.
_REQUIRED_HEADINGS = (
    "things you absolutely need",
    "must have",
    "must-have",
    "required",
    "requirements",
    "what you need",
)
_PREFERRED_HEADINGS = (
    "things we'd like you to have",
    "nice to have",
    "nice-to-have",
    "preferred",
    "good to have",
    "bonus",
)
_DISQUALIFIER_HEADINGS = (
    "things we explicitly do not want",
    "things we explicitly do not want",
    "things we do not want",
    "disqualifiers",
    "do not apply",
    "we will not",
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$", re.MULTILINE)
_EXPERIENCE_RANGE_RE = re.compile(
    r"(\d+)\s*(?:[-–to]+|\s+to\s+)\s*(\d+)\s*\+?\s*years?", re.IGNORECASE
)
_EXPERIENCE_MIN_RE = re.compile(r"(\d+)\s*\+\s*years?", re.IGNORECASE)
_LABEL_RE = re.compile(
    r"^\s*(?P<label>[A-Z][A-Za-z ]{2,30}):\s*(?P<value>.+)$",
    re.MULTILINE,
)


class JDParser:
    """Configurable heuristic JD parser."""

    def __init__(
        self,
        required_headings: Iterable[str] = _REQUIRED_HEADINGS,
        preferred_headings: Iterable[str] = _PREFERRED_HEADINGS,
        disqualifier_headings: Iterable[str] = _DISQUALIFIER_HEADINGS,
    ) -> None:
        self.required_headings = tuple(h.lower() for h in required_headings)
        self.preferred_headings = tuple(h.lower() for h in preferred_headings)
        self.disqualifier_headings = tuple(h.lower() for h in disqualifier_headings)

    def parse(self, text: str) -> JobProfile:
        """Parse a JD text blob into a `JobProfile`.

        Args:
            text: The full JD text, Markdown or plain text.

        Returns:
            A populated `JobProfile`. Fields that cannot be inferred are
            left empty rather than guessed.
        """
        sections = self._split_sections(text)
        labels = self._extract_labels(text)

        required = self._collect_bullets_for(sections, self.required_headings)
        preferred = self._collect_bullets_for(sections, self.preferred_headings)
        disqualifiers = self._collect_bullets_for(
            sections, self.disqualifier_headings
        )

        role_title = self._extract_role_title(text, labels)
        experience_min, experience_max = self._extract_experience(text, labels)
        locations = self._extract_locations(labels)
        industry = labels.get("company") or labels.get("industry")

        return JobProfile(
            role_title=role_title or "Untitled Role",
            industry=industry,
            experience_min_years=experience_min,
            experience_max_years=experience_max,
            locations=locations,
            required_skills=required,
            preferred_skills=preferred,
            mandatory_requirements=required,
            nice_to_have_requirements=preferred,
            disqualifiers=disqualifiers,
            raw_text=text,
        )

    # ------------------------------------------------------------------
    # Section + bullet extraction
    # ------------------------------------------------------------------
    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split `text` into ``(heading, body)`` pairs.

        Returns:
            List of ``(heading_text, body_text)`` tuples. Headings are
            lower-cased; the leading hash characters are stripped.
        """
        matches = list(_HEADING_RE.finditer(text))
        if not matches:
            return [("", text)]

        sections: list[tuple[str, str]] = []
        # Capture any preamble before the first heading.
        if matches[0].start() > 0:
            sections.append(("", text[: matches[0].start()]))
        for i, match in enumerate(matches):
            heading = match.group(2).strip().lower()
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((heading, text[body_start:body_end]))
        return sections

    def _collect_bullets_for(
        self,
        sections: list[tuple[str, str]],
        heading_keywords: tuple[str, ...],
    ) -> list[str]:
        """Return all bullet lines from sections whose heading matches.

        Headings match by substring (so ``"Things you absolutely need"``
        matches the keyword ``"absolutely need"``).
        """
        collected: list[str] = []
        for heading, body in sections:
            if not any(keyword in heading for keyword in heading_keywords):
                continue
            for match in _BULLET_RE.finditer(body):
                bullet = match.group(1).strip()
                if bullet:
                    collected.append(bullet)
        return collected

    # ------------------------------------------------------------------
    # Label / field extraction
    # ------------------------------------------------------------------
    def _extract_labels(self, text: str) -> dict[str, str]:
        """Pull simple ``Label: value`` lines from the top of the JD."""
        labels: dict[str, str] = {}
        for match in _LABEL_RE.finditer(text):
            label = match.group("label").strip().lower()
            value = match.group("value").strip()
            labels.setdefault(label, value)
        return labels

    def _extract_role_title(
        self, text: str, labels: dict[str, str]
    ) -> str | None:
        """Best-effort role title detection."""
        for key in ("job description", "role", "position", "title"):
            if key in labels:
                return labels[key]

        first_heading = next(iter(_HEADING_RE.finditer(text)), None)
        if first_heading:
            heading = first_heading.group(2).strip()
            if ":" in heading:
                heading = heading.split(":", 1)[1].strip()
            return heading or None
        return None

    def _extract_experience(
        self, text: str, labels: dict[str, str]
    ) -> tuple[float | None, float | None]:
        """Extract ``(min_years, max_years)`` from the JD."""
        candidate_blobs = [labels.get("experience required", ""), text]
        for blob in candidate_blobs:
            if not blob:
                continue
            range_match = _EXPERIENCE_RANGE_RE.search(blob)
            if range_match:
                return (
                    float(range_match.group(1)),
                    float(range_match.group(2)),
                )
            min_match = _EXPERIENCE_MIN_RE.search(blob)
            if min_match:
                return float(min_match.group(1)), None
        return None, None

    def _extract_locations(self, labels: dict[str, str]) -> list[str]:
        """Split the ``Location:`` label into a list of cities."""
        location_value = labels.get("location")
        if not location_value:
            return []
        parts = re.split(r"[,/|]| or | and ", location_value)
        return [p.strip() for p in parts if p.strip()]


def parse_job_description(text: str) -> JobProfile:
    """Convenience wrapper that uses default `JDParser` configuration.

    Args:
        text: Raw JD text.

    Returns:
        Heuristically parsed `JobProfile`.
    """
    return JDParser().parse(text)
