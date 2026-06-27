"""File-system loaders for raw hackathon assets."""

from app.intelligence.loaders.candidate_loader import CandidateLoader
from app.intelligence.loaders.jd_loader import load_jd_text, load_job_profile_yaml

__all__ = ["CandidateLoader", "load_jd_text", "load_job_profile_yaml"]
