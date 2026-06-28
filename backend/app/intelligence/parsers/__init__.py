"""Parsers transform raw dicts / text into typed intelligence objects."""

from app.intelligence.parsers.candidate_parser import CandidateParser
from app.intelligence.parsers.jd_parser import JDParser, parse_job_description
from app.intelligence.parsers.job_extractor import (
    JobExtraction,
    JobExtractor,
    extract_job_intelligence,
)

__all__ = [
    "CandidateParser",
    "JDParser",
    "JobExtraction",
    "JobExtractor",
    "extract_job_intelligence",
    "parse_job_description",
]
