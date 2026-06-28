"""Skill taxonomy and normalization.

The skill normalizer is the canonical bridge between free-text skill
strings (as they appear in candidate profiles from Phase 2 and in job
descriptions) and a stable canonical form used for matching.

Public surface:

* :class:`SkillNormalizer` — alias-aware normalization with optional
  taxonomy-based categorization.
* :data:`SKILL_ALIASES` — curated alias → canonical map.
* :data:`SKILL_TAXONOMY` — canonical skill → category map (used by the
  job extractor to bucket extracted skills).
"""

from app.intelligence.skills.normalizer import (
    SKILL_ALIASES,
    SkillCategory,
    SkillNormalizer,
)
from app.intelligence.skills.taxonomy import SKILL_TAXONOMY, SOFT_SKILL_KEYWORDS

__all__ = [
    "SKILL_ALIASES",
    "SKILL_TAXONOMY",
    "SOFT_SKILL_KEYWORDS",
    "SkillCategory",
    "SkillNormalizer",
]
