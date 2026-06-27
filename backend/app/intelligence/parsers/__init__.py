"""Parsers transform raw dicts / text into typed intelligence objects."""

from app.intelligence.parsers.candidate_parser import CandidateParser
from app.intelligence.parsers.jd_parser import JDParser, parse_job_description

__all__ = ["CandidateParser", "JDParser", "parse_job_description"]
