"""Intelligence layer: dataset → structured objects → features → explanations.

The intelligence layer is the engine room of Scryve's ranking system.
Submodules are layered:

* `loaders/`           - read raw files (JSONL, JSON Schema, JD documents)
* `preprocessors/`     - low-level text/date helpers
* `parsers/`           - raw dicts → typed `Candidate` / `JobProfile`
* `analyzers/`         - higher-order analyses (career stability, ...)
* `feature_engineering/` - normalized features per candidate
* `embeddings/`        - reserved for Sprint 3 (semantic vectors)
* `ranking/`           - reserved for Sprint 4 (scoring / ordering)
* `explainability/`    - structured explanations of matches and gaps
"""

from app.intelligence.domain import (
    BehavioralSignals,
    Candidate,
    CandidateExplanation,
    CandidateFeatures,
    CandidateProfile,
    CertificationEntry,
    EducationEntry,
    ExperienceEntry,
    JobProfile,
    LanguageEntry,
    Skill,
)

__all__ = [
    "BehavioralSignals",
    "Candidate",
    "CandidateExplanation",
    "CandidateFeatures",
    "CandidateProfile",
    "CertificationEntry",
    "EducationEntry",
    "ExperienceEntry",
    "JobProfile",
    "LanguageEntry",
    "Skill",
]
